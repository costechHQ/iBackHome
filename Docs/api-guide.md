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
| `POST /api/v1/milestones/{id}/claim` | the project's contractor | The work is done, so `funded` becomes `claimed`. Send an `Idempotency-Key` header; a retry with the same key gets the first answer back. |

Errors from claim:

| Status | Code | Meaning |
| --- | --- | --- |
| 401 | `unauthorized` | No valid sign-in token |
| 403 | `forbidden_role` | The signed-in user is not a contractor |
| 403 | `transition_not_allowed` | Raised by the service when a non-contractor reaches it (the route refuses them first) |
| 403 | `not_project_contractor` | The user is a contractor, but not on this project |
| 404 | `milestone_not_found` | No milestone has this ID |
| 409 | `project_not_active` | The project is draft, in BoQ review, paused or completed |
| 409 | `invalid_transition` | The milestone is not `funded` (it isn't funded yet, or it has already been claimed) |
| 503 | `projects_not_ready` | Projects are not connected yet (see below) |

Service functions for other features (they never commit; the caller does): `create_for_project()` (Christopher), plus `mark_funded()`, `mark_released()`, `mark_disputed()` and `mark_resolved()` (Gabriel).

## Sign-in

Sign-in is connected (Christopher's `app.base.users`). `app/base/audit/actor.py` turns the signed-in user into an `Actor(id, role)` through `current_actor` / `CurrentActor`. To limit a route to one role, add `dependencies=[Depends(users.require_role("ops"))]` (`from app.base.users import service as users`). No token returns 401, a wrong role returns 403 `forbidden_role`. In tests, sign in with a real token: `users.create_access_token(user)` in an `Authorization: Bearer ...` header.

## Connecting projects

`app/features/milestones/project_check.py` has `get_project_info`, which tells a claim the project's status and contractor. Until Christopher's projects feature is merged, it answers 503 `projects_not_ready`. Once his projects service is in main, replace its body with a call to his service, for example:

```python
from app.features.projects import service as projects

async def get_project_info(session: AsyncSession, project_id: uuid.UUID) -> ProjectInfo:
    project = await projects.get_project(session, project_id)
    return ProjectInfo(id=project.id, status=project.status, contractor_id=project.contractor_id)
```

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
