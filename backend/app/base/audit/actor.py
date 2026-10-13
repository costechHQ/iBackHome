"""Who is making this request.

`current_actor` is the one place where the audit log and milestones learn the signed-in user.
Until Christopher's login (`current_user`) is merged it refuses every request with
503 `auth_not_ready`, so no endpoint is ever open by accident. Tests replace it with
`app.dependency_overrides[current_actor]`.

When Christopher's code is in main, replace the body of `current_actor` with a call to his
`current_user` (see docs/api-guide.md, "Connecting sign-in"). Nothing else changes.
"""

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from app.core.errors import AppError


@dataclass(frozen=True)
class Actor:
    id: uuid.UUID
    role: str  # client | contractor | supervisor | supplier | ops


async def current_actor() -> Actor:
    raise AppError("auth_not_ready", "Sign-in is not connected yet.", 503)


CurrentActor = Annotated[Actor, Depends(current_actor)]
