"""Audit log: record(), the database refusing edits, and GET /ops/audit."""

import secrets
import uuid
from collections.abc import Callable

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Executable
from starlette.requests import Request

from app.base import audit
from app.base.audit.models import AuditEntry
from app.base.users import service as users
from app.base.users.models import User
from app.core.errors import AppError
from app.features.milestones.models import Milestone, MilestoneStatus


def fake_request(ip: str = "102.89.1.10", device_id: str | None = "pixel-7a-abc") -> Request:
    headers = [(b"x-device-id", device_id.encode())] if device_id else []
    return Request({"type": "http", "method": "POST", "path": "/", "headers": headers, "client": (ip, 5000)})


async def add_entry(
    session: AsyncSession, action: str = "thing.done", actor_id: uuid.UUID | None = None
) -> AuditEntry:
    return await audit.record(session, actor_id or uuid.uuid4(), action, "thing", uuid.uuid4())


# --- record() --------------------------------------------------------------------------------


async def test_record_saves_everything(db_session: AsyncSession) -> None:
    actor_id, object_id = uuid.uuid4(), uuid.uuid4()
    entry = await audit.record(
        db_session,
        actor_id,
        "milestone.claimed",
        "milestone",
        object_id,
        before={"status": MilestoneStatus.FUNDED, "id": object_id},
        after={"status": "claimed"},
        request=fake_request(),
    )
    saved = await db_session.scalar(select(AuditEntry).where(AuditEntry.id == entry.id))
    assert saved is not None
    assert (saved.actor_id, saved.action, saved.object_type, saved.object_id) == (
        actor_id,
        "milestone.claimed",
        "milestone",
        object_id,
    )
    assert saved.before == {"status": "funded", "id": str(object_id)}  # enums and UUIDs made JSON-safe
    assert saved.after == {"status": "claimed"}
    assert (saved.ip, saved.device_id) == ("102.89.1.10", "pixel-7a-abc")
    assert saved.at is not None


async def test_record_for_the_system_without_request(db_session: AsyncSession) -> None:
    entry = await audit.record(db_session, None, "milestone.funded", "milestone", uuid.uuid4())
    assert (entry.actor_id, entry.ip, entry.device_id, entry.before, entry.after) == (None,) * 5


async def test_snapshot_gives_json_safe_columns(db_session: AsyncSession) -> None:
    milestone = Milestone(
        project_id=uuid.uuid4(), sequence=1, name="Foundation", amount_minor=1_000, currency="NGN"
    )
    milestone.status = MilestoneStatus.PENDING
    data = audit.snapshot(milestone)
    assert data["status"] == "pending"
    assert data["project_id"] == str(milestone.project_id)
    assert data["amount_minor"] == 1_000


# --- the database refuses edits ----------------------------------------------------------------


@pytest.mark.parametrize(
    "statement",
    [
        lambda: update(AuditEntry).values(action="covered.up"),
        lambda: delete(AuditEntry),
        lambda: text("TRUNCATE audit_log"),
    ],
    ids=["update", "delete", "truncate"],
)
async def test_database_refuses_to_change_audit_entries(
    db_session: AsyncSession, statement: Callable[[], Executable]
) -> None:
    entry = await add_entry(db_session)
    with pytest.raises(DBAPIError, match="insert-only"):
        async with db_session.begin_nested():
            await db_session.execute(statement())
    still_there = await db_session.scalar(select(AuditEntry.action).where(AuditEntry.id == entry.id))
    assert still_there == "thing.done"


async def test_app_user_has_no_update_or_delete_rights(db_session: AsyncSession) -> None:
    rights = await db_session.scalar(
        text(
            "SELECT has_table_privilege(current_user, 'audit_log', 'UPDATE') "
            "OR has_table_privilege(current_user, 'audit_log', 'DELETE')"
        )
    )
    is_superuser = await db_session.scalar(text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user"))
    # A superuser (local Docker) always "has" every right; the trigger above stops it instead.
    assert rights is False or is_superuser is True


# --- search() and GET /ops/audit -------------------------------------------------------------


async def test_search_filters_and_pages_newest_first(db_session: AsyncSession) -> None:
    actor_id = uuid.uuid4()
    entries = [await add_entry(db_session, f"test.step{i}", actor_id=actor_id) for i in range(5)]
    await add_entry(db_session, "test.other")

    page1, cursor = await audit.service.search(db_session, actor_id=actor_id, limit=2)
    page2, cursor2 = await audit.service.search(db_session, actor_id=actor_id, limit=2, cursor=cursor)
    page3, cursor3 = await audit.service.search(db_session, actor_id=actor_id, limit=2, cursor=cursor2)

    got = [e.action for e in page1 + page2 + page3]
    assert got == [e.action for e in reversed(entries)]
    assert cursor3 is None


async def test_search_rejects_a_broken_cursor(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as error:
        await audit.service.search(db_session, cursor="not-a-cursor")
    assert error.value.code == "invalid_cursor"


async def sign_in_as(session: AsyncSession, role: str) -> dict[str, str]:
    """A real user with this role, and the Authorization header for their access token."""
    user = User(phone=f"+234803{secrets.randbelow(10**7):07d}", role=role, status="active")
    session.add(user)
    await session.flush()
    return {"Authorization": f"Bearer {users.create_access_token(user)}"}


async def test_ops_can_search_the_audit_log(client: AsyncClient, db_session: AsyncSession) -> None:
    entry = await add_entry(db_session, "test.searchable")
    headers = await sign_in_as(db_session, "ops")
    response = await client.get("/api/v1/ops/audit", params={"action": "test.searchable"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [str(entry.id)]
    assert body["next_cursor"] is None


@pytest.mark.parametrize("role", ["client", "contractor", "supervisor", "supplier"])
async def test_only_ops_can_search_the_audit_log(
    client: AsyncClient, db_session: AsyncSession, role: str
) -> None:
    headers = await sign_in_as(db_session, role)
    response = await client.get("/api/v1/ops/audit", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_role"


async def test_audit_log_needs_sign_in(client: AsyncClient) -> None:
    response = await client.get("/api/v1/ops/audit")
    assert response.status_code == 401


async def test_limit_is_checked(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await sign_in_as(db_session, "ops")
    response = await client.get("/api/v1/ops/audit", params={"limit": 500}, headers=headers)
    assert response.status_code == 422
