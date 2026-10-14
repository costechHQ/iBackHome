"""Who is making this request.

`current_actor` turns the signed-in user (Christopher's `users.CurrentUserDep`) into the small
`Actor` that milestones and the audit log work with. A missing or bad token is refused with 401
before the route runs. Routes that need a particular role add
`dependencies=[Depends(users.require_role("..."))]`; a wrong role returns 403 `forbidden_role`.

Tests sign in with a real token (`users.create_access_token`), not a stand-in.
"""

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from app.base.users import service as users


@dataclass(frozen=True)
class Actor:
    id: uuid.UUID
    role: str  # client | contractor | supervisor | supplier | ops


async def current_actor(user: users.CurrentUserDep) -> Actor:
    return Actor(id=user.id, role=user.role)


CurrentActor = Annotated[Actor, Depends(current_actor)]
