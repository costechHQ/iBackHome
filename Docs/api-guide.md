# iBackHome API guide

Owner: Lilian. This is how the rest of the team uses the parts of the backend Lilian owns. The full list of endpoints is at `http://localhost:8000/docs`.

## Calling the API from the web and Flutter apps

The rules every screen follows. Endpoint details are in `/docs` (generate the API types from `/openapi.json`; don't write them by hand).

**Base URL and headers**

- Every endpoint is under `/api/v1`, JSON in and out, times in UTC (ISO 8601). Show them in the user's own time zone (`GET /me` returns `timezone`).
- Signed-in calls send `Authorization: Bearer <access_token>`.
- The apps send `X-Device-Id` (a stable ID per install) on every request; it is saved on audit entries.
- Every response carries `X-Request-ID`. Show it in error reports so a problem can be found in the logs (you may also send your own).

**Signing in (OTP)**

1. `POST /api/v1/auth/otp/request` with `{"identifier": "+447700900123", "channel": "whatsapp"}`. The identifier is a phone (any country; a Nigerian number without + such as `08031234567` is accepted) or an email. `channel` is `sms` (default) or `whatsapp` for a phone, `email` for an email. Answer: `{"status": "sent", "expires_in": 300}`. Too many requests: 429 with a `Retry-After` header.
2. `POST /api/v1/auth/otp/verify` with `{"identifier": "...", "code": "482913"}`. Answer: `{"access_token", "refresh_token", "token_type": "bearer", "expires_in"}`. Five wrong codes: 429 `too_many_attempts` (request a new code).
3. `GET /api/v1/me`: who is signed in and their `role` (`client`, `contractor`, `supervisor`, `supplier`, `ops`). Show only that role's screens.
4. The access token lasts 15 minutes. `POST /api/v1/auth/refresh` with `{"refresh_token": "..."}` gives a new pair, and the old refresh token stops working. **Never retry a refresh blindly and never run two at once:** reusing a refresh token signs the user out on every device. Keep one refresh in flight; if it fails, send the user to sign in. Flutter keeps tokens in encrypted storage; the web keeps the access token in memory.

**Errors**

Every error has one shape: `{"error": {"code": "milestone_not_verified", "message": "Text you can show the user."}}`. Branch on `code` (it never changes); show `message`. Common ones: 401 `unauthorized` (sign in again), 403 `forbidden_role` (wrong role) or `not_project_member`, 404 `*_not_found`, 409 for a state that doesn't allow the action (e.g. `invalid_transition`, `project_not_active`, `site_locked`), 422 `validation_error` for a bad body, 429 too many requests, 503 when a dependency is down (retry later).

**Writes: `Idempotency-Key`**

Send a new UUID as `Idempotency-Key` on every POST/PUT a user triggers, and **the same key when you retry that action** (after a timeout or from the offline queue). A repeat returns the first answer instead of doing the work twice. 409 `idempotency_key_in_use` means the first request is still running: wait a moment and retry with the same key. Sign-in (`/auth/otp/verify`, `/auth/refresh`) never replays.

**Lists: pagination**

Lists take `?limit=` and `?cursor=`. The answer is `{"items": [...], "next_cursor": "..."}`; pass `next_cursor` back as `cursor` for the next page. It is `null` on the last page. Don't build or read cursors yourself.

**Money**

Amounts are integers in minor units with a currency: `{"amount_minor": 800000000, "currency": "NGN"}` is ₦8,000,000.00. Never use floats; format only for display. Every amount the user sees comes from the API (the ledger), never from the app's own arithmetic.

**The main flows, in order**

1. **Sign in** (above), then `GET /me`.
2. **Project setup:** client `POST /projects` (optional `contractor_phone` invites the contractor) → client `PUT /projects/{id}/site` (pin + GeoJSON geofence; the pin inside it) → contractor `PUT /projects/{id}/boq` → client, contractor and ops `POST /projects/{id}/boq/approve` (the third approval makes the project `active` and creates the milestones) → ops `POST /projects/{id}/supervisor`.
3. **Funding:** client `POST /projects/{id}/funding` → open the Stripe Checkout URL → after returning, refresh `GET /projects/{id}/milestones` until the milestone is `funded` (the webhook decides, not the redirect).
4. **Evidence (Flutter):** `POST /devices` once per install → per capture `POST /evidence/upload-url` → PUT the file to that URL → `POST /evidence` with metadata and signature (see `features/evidence/SIGNING.md`) → the status becomes `accepted`, `rejected` (with a reason) or `flagged`. Gallery: `GET /projects/{id}/evidence`.
5. **Milestone:** contractor `POST /milestones/{id}/claim` → supervisor `POST /milestones/{id}/verify` → client `POST /milestones/{id}/approve` → `released` when escrow confirms. Or client `POST /milestones/{id}/disputes` → ops `POST /disputes/{id}/resolve` (two different ops users).
6. **Materials:** contractor `POST /projects/{id}/orders` → client `POST /orders/{id}/approve` → supervisor `POST /orders/{id}/delivery`.
7. **Reports and money:** `GET /projects/{id}/reports` (supervisor or ops `POST /reports/{id}/review`), `GET /projects/{id}/ledger`, `GET /price-index`, `POST /quotes/check`.
8. **Ops:** `GET /ops/queue`, `POST /supervisors/{id}/vetting`, `POST /projects/{id}/spot-checks`, `POST /evidence/{id}/decision`, `GET /ops/audit`.

The apps don't send messages themselves: the backend notifies people (see "Milestone messages" below).


## Audit log

Every state change writes one audit entry, in the same transaction as the change. If the change is rolled back, so is the entry.

```python
from app.base import audit

before = audit.snapshot(order)          # the row's columns, JSON-safe
order.status = "approved"
await audit.record(
    session,
    actor.id,                           # None when the system acts (webhooks, scheduled jobs)
    "order.approved",                   # "<object>.<what happened>"
    "order",                            # object_type
    order.id,                           # object_id
    before=before,
    after=audit.snapshot(order),
    request=request,                    # pass the FastAPI Request so the IP and device are saved
)
await session.commit()                  # you commit, not record()
```

Rules:

- Never put OTPs, tokens, passwords or keys in `before` or `after`.
- Milestone moves are audited for you inside `milestones.service.transition()`, so don't audit them again.
- The table is insert-only. The database refuses every UPDATE, DELETE and TRUNCATE (a trigger, plus those rights removed from the app's database user), so there is no way to fix an entry. Write a new one instead.
- Apps send the device ID in the `X-Device-Id` header on every request; it is saved on each entry.

**Search (ops only; other roles get 403 `forbidden_role`):** `GET /api/v1/ops/audit`, newest first. Optional filters are `actor_id`, `action`, `object_type`, `object_id`, `since` and `until` (ISO date-times), plus `limit` (1–200, default 50) and `cursor`. The response is `{"items": [...], "next_cursor": "..."}`. To get the next page, pass `next_cursor` back as `cursor`. It is `null` on the last page.

## Milestones

| Endpoint | Who | What it does |
| --- | --- | --- |
| `POST /api/v1/milestones/{id}/claim` | the project's contractor | The work is done: `funded` → `claimed`. |
| `POST /api/v1/milestones/{id}/verify` | the project's assigned supervisor | `verified` with a checklist: `claimed` → `verified`. `rejected` with a reason: back to `funded` for rework. |
| `POST /api/v1/milestones/{id}/approve` | the project's client | `verified` → `approved`, and escrow is asked to release the money (`escrow.request_release()`). The milestone becomes `released` when the escrow partner confirms. |
| `GET /api/v1/projects/{id}/milestones` | the project's client, contractor, assigned supervisor, and ops | The milestones in order, each with `latest_verification` (so the contractor can see why a claim was rejected). |

All three POSTs need a project that is `active` and accept an `Idempotency-Key` header: a retry with the same key gets the first answer back (the mobile sync queue relies on this).

**Verify body:**

```json
{
  "decision": "verified",
  "checklist": [
    {"item": "Trench depth as drawn", "passed": true, "evidence_ids": ["<evidence uuid>"]},
    {"item": "Rebar spacing 150 mm", "passed": true, "evidence_ids": ["<evidence uuid>", "<evidence uuid>"]}
  ],
  "notes": "optional"
}
```

```json
{"decision": "rejected", "notes": "Blockwork not plumb on the east wall", "checklist": []}
```

- `verified`: at least one checklist item; every item `passed` and with at least one photo (`evidence_ids`, up to 20 per item, up to 50 items). Every photo must be this milestone's **accepted supervisor evidence** (`evidence.accepted_for_milestone()`): contractor uploads, and photos still being checked, flagged or rejected, don't count.
- `rejected`: `notes` is required (the reason the contractor sees). Nothing about evidence is checked.
- The response is `{"milestone": {...}, "verification": {...}}`.

Errors:

| Status | Code | Meaning |
| --- | --- | --- |
| 401 | `unauthorized` | No valid sign-in token |
| 403 | `forbidden_role` | Wrong role for this endpoint (claim: contractor, verify: supervisor, approve: client) |
| 403 | `not_project_contractor` / `not_assigned_supervisor` / `not_project_client` | Right role, but not on this project |
| 403 | `not_project_member` | List: not the project's client, contractor or supervisor, and not ops |
| 404 | `milestone_not_found` / `project_not_found` | No such milestone or project |
| 409 | `project_not_active` | The project is draft, in BoQ review, paused or completed |
| 409 | `invalid_transition` | The milestone is in the wrong state (claim needs `funded`, verify `claimed`, approve `verified`); also a queued offline verification after the milestone was disputed |
| 409 | `evidence_not_accepted` | Verify: some checklist photos are not accepted supervisor evidence for this milestone yet |
| 422 | `validation_error` | Bad body (e.g. a verified checklist with a failed item or no photo, a rejection without a reason) |

Every move writes an audit entry (`milestone.<status>`); each verification also writes `verification.verified` or `verification.rejected`.

Service functions for other features (they never commit; the caller does): `create_for_project()` (Christopher); `mark_funded()`, `mark_released()`, `mark_disputed()` and `mark_resolved()` (Gabriel); `list_verifiers(session, project_id)` (James's rotation: who verified each verified milestone, in milestone order; a milestone sent back for rework drops out).

## Sign-in

Sign-in is connected (Christopher's `app.base.users`). `app/base/audit/actor.py` turns the signed-in user into an `Actor(id, role)` through `current_actor` / `CurrentActor`. To limit a route to one role, add `dependencies=[Depends(users.require_role("ops"))]` (`from app.base.users import service as users`). No token returns 401, a wrong role returns 403 `forbidden_role`. In tests, sign in with a real token: `users.create_access_token(user)` in an `Authorization: Bearer ...` header.

## Connecting projects and evidence

- Milestones read the project's status, client, contractor and assigned supervisor through `projects.get_project()`. `milestones.project_id` is a foreign key to `projects.id`.
- `app/features/milestones/evidence_check.py` asks Abigail's `evidence.accepted_for_milestone()` for the milestone's accepted supervisor photos.

## Notifications

```python
from app.base.notifications import Template, notify

MILESTONE_CLAIMED = Template(
    name="milestone.claimed",                 # saved on the notifications row
    title="Milestone claimed",                # push title and email subject
    text="{contractor} says '{milestone}' is done. Your supervisor will check it next.",
)

await notify(session, client.id, MILESTONE_CLAIMED, {"contractor": "Obi Builders", "milestone": "Foundation"})
await session.commit()                        # the caller commits
```

- **Order:** WhatsApp → push → SMS → email, stopping at the first channel that delivers. Pass `channels=["email", "sms"]` to choose your own order. For "WhatsApp + email" (both), call `notify()` once per channel.
- A channel is skipped when the user has no address for it (no email, no push token yet) or it isn't configured.
- **It never raises because a provider is down.** If every channel fails it saves a `failed` row, which `notifications.retry_failed` retries every 10 minutes on all channels (for up to 24 hours or 20 channel tries).
- It raises 404 `user_not_found` for an unknown user, and `ValueError` if a `{placeholder}` in the template is missing from `data`.
- Send **after** committing the change the message is about, so nobody hears about something that was rolled back.
- Each feature keeps its templates in its own `messages.py`. Use plain `{name}` placeholders only.
- **Send once:** pass `key="..."` from background jobs. A second `notify()` with the same user, template and key returns the first row and sends nothing.

**Login codes:** `notify_address(session, identifier, channel, LOGIN_CODE, {"code": code})` sends to a raw phone (E.164) or email on exactly that channel, with no user needed. The code is never stored. It raises 503 `notifications_not_configured` when that channel can't send here, and 502 `notification_failed` when the provider refuses.

**Channels:** email over SMTP (any provider), SMS through Termii, push through Firebase Cloud Messaging, WhatsApp through Meta's WhatsApp Business Cloud API. On `ENVIRONMENT=local`, a channel that isn't configured writes the message to the API log instead; staging and production never do.

**Environment variables** (empty means that channel is off):

| Variable | Example |
| --- | --- |
| `NOTIFY_TIMEOUT_SECONDS` | `10` |
| `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, `EMAIL_SMTP_USERNAME`, `EMAIL_SMTP_PASSWORD`, `EMAIL_SMTP_STARTTLS`, `EMAIL_FROM` | `smtp-relay.brevo.com`, `587`, …, `true`, `iBackHome <no-reply@ibackhome.ng>` |
| `TERMII_API_KEY`, `TERMII_SENDER_ID`, `TERMII_BASE_URL` | …, `iBackHome`, `https://api.ng.termii.com` |
| `FCM_PROJECT_ID`, `FCM_SERVICE_ACCOUNT_JSON` | the Firebase project ID, and the service account key file's contents on one line |
| `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` | a system-user token, and the sending number's ID from WhatsApp Manager |
| `WHATSAPP_API_VERSION`, `WHATSAPP_BASE_URL`, `WHATSAPP_LANGUAGE`, `WHATSAPP_USE_TEMPLATES` | `v23.0`, `https://graph.facebook.com`, `en`, `true` |
| `NOTIFY_RETRY_HOURS`, `NOTIFY_MAX_ATTEMPTS` | `24`, `20` |

**WhatsApp templates.** WhatsApp lets a business start a conversation only with a template Meta has approved. A `Template` with `whatsapp_template="name"` is sent as that template, its placeholders becoming `{{1}}`, `{{2}}`... in the order they first appear in `text`. Submit each one in WhatsApp Manager with the same wording before turning WhatsApp on (category: utility; the login code: authentication, with a copy-code button). A template without `whatsapp_template` goes as plain text, which Meta accepts only within 24 hours of the person writing to us; otherwise `notify()` falls back to the next channel. `WHATSAPP_USE_TEMPLATES=false` sends everything as plain text (for test numbers that have written first).

## Milestone messages

`milestones.service.transition()` queues the messages itself, so callers (Gabriel's `mark_released()`, the claim, verify and approve routes) do nothing extra. The task `milestones.send_update` is queued only **after the transaction commits** (a rolled-back move tells nobody), and every send has a key, so a task that runs twice sends nothing new.

| Event | Client | Contractor | Supervisor |
| --- | --- | --- | --- |
| Milestone claimed | WhatsApp | | push |
| Milestone verified | WhatsApp + email (amount to approve) | push | |
| Claim rejected | | push (with the supervisor's reason) | |
| Release completed (approved or dispute resolved) | WhatsApp + email (amount) | WhatsApp (amount) | |
| `milestones.remind`, daily 09:00 WAT | verified over 48 h, not approved | | claim waiting over 24 h |

"Push" means push first, then the usual fallback (push tokens aren't stored yet, so today it is WhatsApp, SMS or email). Amounts come from the milestone (`amount_minor` + `currency`, formatted with integers only, e.g. `NGN 8,000,000.00`). The templates are in `app/features/milestones/messages.py`; their WhatsApp names are `milestone_claimed_client`, `milestone_claimed_supervisor`, `milestone_verified_client`, `milestone_verified_contractor`, `milestone_rejected_contractor`, `milestone_released_client`, `milestone_released_contractor`, `milestone_remind_client` and `milestone_remind_supervisor`.

To see what was sent: the `notifications` table has one row per send (`status` `sent` or `failed`, the `channel` used, and in `error` why earlier channels failed).
