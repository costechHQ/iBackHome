"""HTTP endpoints for the ops console. Owner: Abigail."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.base.users import service as users
from app.base.users.models import User
from app.core import pagination
from app.core.db import SessionDep
from app.features.ops import service
from app.features.ops.schemas import OpsQueue

router = APIRouter(tags=["ops"])

OpsUser = Annotated[User, Depends(users.require_role("ops"))]


@router.get("/ops/queue", response_model=OpsQueue)
async def ops_queue(
    session: SessionDep,
    ops: OpsUser,
    limit: Annotated[int, Query(ge=1, le=pagination.MAX_LIMIT)] = service.DEFAULT_LIMIT,
) -> OpsQueue:
    """Vetting requests, flagged evidence and open disputes, oldest first."""
    return await service.get_queue(session, limit)
