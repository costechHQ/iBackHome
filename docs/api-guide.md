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

**Search (ops only):** `GET /api/v1/ops/audit`, newest first. Optional filters are `actor_id`, `action`, `object_type`, `object_id`, `since` and `until` (ISO date-times), plus `limit` (1–200, default 50) and `cursor`. The response is `{"items": [...], "next_cursor": "..."}`. To get the next page, pass `next_cursor` back as `cursor`. It is `null` on the last page.

## Milestones

| Endpoint | Who | What it does |
| --- | --- | --- |
| `POST /api/v1/milestones/{id}/claim` | the project's contractor | The work is done, so `funded` becomes `claimed`. Send an `Idempotency-Key` header; a retry with the same key gets the first answer back. |

Errors from claim:

| Status | Code | Meaning |
| --- | --- | --- |
| 403 | `transition_not_allowed` | The user is not a contractor |
| 403 | `not_project_contractor` | The user is a contractor, but not on this project |
| 404 | `milestone_not_found` | No milestone has this ID |
| 409 | `project_not_active` | The project is draft, in BoQ review, paused or completed |
| 409 | `invalid_transition` | The milestone is not `funded` (it isn't funded yet, or it has already been claimed) |
| 503 | `auth_not_ready` / `projects_not_ready` | Sign-in or projects are not connected yet (see below) |

Service functions for other features (they never commit; the caller does): `create_for_project()` (Christopher), plus `mark_funded()`, `mark_released()`, `mark_disputed()` and `mark_resolved()` (Gabriel).

## Connecting sign-in

`app/base/audit/actor.py` has `current_actor`, which tells the audit log and milestones who is signed in. Until Christopher's login is merged, it answers 503 `auth_not_ready`, so no endpoint can be used without signing in. Once his `current_user` is in main, replace the function with this (adjust the import to wherever his code lives):

```python
from app.base.users.deps import current_user   # Christopher's
from app.base.users.models import User

async def current_actor(user: Annotated[User, Depends(current_user)]) -> Actor:
    return Actor(id=user.id, role=user.role)
```

## Connecting projects

`app/features/milestones/project_check.py` has `get_project_info`, which tells a claim the project's status and contractor. Until Christopher's projects feature is merged, it answers 503 `projects_not_ready`. Once his projects service is in main, replace its body with a call to his service, for example:

```python
from app.features.projects import service as projects

async def get_project_info(session: AsyncSession, project_id: uuid.UUID) -> ProjectInfo:
    project = await projects.get_project(session, project_id)
    return ProjectInfo(id=project.id, status=project.status, contractor_id=project.contractor_id)
```
