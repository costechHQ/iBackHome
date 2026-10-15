# iBackHome API guide

Owner: Lilian. This is how the rest of the team uses the parts of the backend Lilian owns. The full list of endpoints is at `http://localhost:8000/docs`.

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
- **It never raises because a provider is down.** If every channel fails it saves a `failed` row, which `notifications.retry_failed` (backend day 5) retries.
- It raises 404 `user_not_found` for an unknown user, and `ValueError` if a `{placeholder}` in the template is missing from `data`.
- Send **after** committing the change the message is about, so nobody hears about something that was rolled back.
- Each feature keeps its templates in its own `messages.py`. Use plain `{name}` placeholders only.

**Login codes:** `notify_address(session, identifier, channel, LOGIN_CODE, {"code": code})` sends to a raw phone (E.164) or email on exactly that channel, with no user needed. The code is never stored. It raises 503 `notifications_not_configured` when that channel can't send here, and 502 `notification_failed` when the provider refuses.

**Channels:** email over SMTP (any provider), SMS through Termii, push through Firebase Cloud Messaging, WhatsApp on backend day 5. On `ENVIRONMENT=local`, a channel that isn't configured writes the message to the API log instead; staging and production never do.

**Environment variables** (empty means that channel is off):

| Variable | Example |
| --- | --- |
| `NOTIFY_TIMEOUT_SECONDS` | `10` |
| `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, `EMAIL_SMTP_USERNAME`, `EMAIL_SMTP_PASSWORD`, `EMAIL_SMTP_STARTTLS`, `EMAIL_FROM` | `smtp-relay.brevo.com`, `587`, …, `true`, `iBackHome <no-reply@ibackhome.ng>` |
| `TERMII_API_KEY`, `TERMII_SENDER_ID`, `TERMII_BASE_URL` | …, `iBackHome`, `https://api.ng.termii.com` |
| `FCM_PROJECT_ID`, `FCM_SERVICE_ACCOUNT_JSON` | the Firebase project ID, and the service account key file's contents on one line |
