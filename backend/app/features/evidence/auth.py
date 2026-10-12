"""Who is calling, and which role they have.

Stand-in until Christopher's `current_user` and `require_role` (base/users, Day 2) are on main.
Only this file knows about it: when they land, replace the body here with imports from
app.base.users.service and nothing else in evidence changes. Until then every call gets 401,
and tests override `current_actor`.
"""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from app.core.errors import AppError


@dataclass(frozen=True)
class Actor:
    id: uuid.UUID
    role: str  # client | contractor | supervisor | supplier | ops


async def current_actor() -> Actor:
    raise AppError("unauthorized", "Sign-in is not available yet.", 401)


CurrentActor = Annotated[Actor, Depends(current_actor)]


def require_roles(*roles: str) -> Callable[[Actor], Awaitable[Actor]]:
    async def check(actor: CurrentActor) -> Actor:
        if actor.role not in roles:
            raise AppError("forbidden", "Your role cannot do this.", 403)
        return actor

    return check
