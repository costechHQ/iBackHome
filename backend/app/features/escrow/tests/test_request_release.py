"""request_release is a stub on day 2; these tests pin the signature Lilian codes against."""

import inspect
import uuid
from typing import get_type_hints

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.features.escrow import service as escrow
from app.features.escrow.service import PLACEHOLDER_RELEASE_ID, ReleaseRequest, request_release


def test_signature_is_the_agreed_one():
    assert inspect.iscoroutinefunction(request_release)
    assert list(inspect.signature(request_release).parameters) == ["session", "milestone_id", "actor"]
    hints = get_type_hints(request_release)
    assert hints["session"] is AsyncSession
    assert hints["milestone_id"] is uuid.UUID
    assert hints["actor"] is User
    assert hints["return"] is ReleaseRequest


async def test_stub_returns_the_placeholder_and_touches_nothing():
    milestone_id = uuid.uuid4()

    class _NoSession:
        def __getattr__(self, name: str) -> object:
            raise AssertionError(f"the stub must not use the session (called {name})")

    result = await escrow.request_release(_NoSession(), milestone_id, User())  # type: ignore[arg-type]

    assert result == ReleaseRequest(
        release_id=PLACEHOLDER_RELEASE_ID, milestone_id=milestone_id, status="requested"
    )
