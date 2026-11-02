"""GET /me/notifications and POST /me/notifications/{id}/read: the signed-in user's own feed."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.notifications import LOGIN_CODE, Template
from app.base.notifications.models import Notification
from app.base.users import service as users
from app.base.users.models import User

CLAIMED = Template(
    name="test.feed_claimed",
    title="Milestone claimed",
    text="{contractor} says '{milestone}' is done.",
)
T0 = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
NO_ID = "00000000-0000-0000-0000-000000000000"


async def make_user(session: AsyncSession, role: str = "client") -> User:
    user = User(phone=f"+234803{secrets.randbelow(10**7):07d}", role=role, status="active")
    session.add(user)
    await session.flush()
    return user


def auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {users.create_access_token(user)}"}


async def add(
    session: AsyncSession,
    user: User | None,
    *,
    minutes: int = 0,
    template: str = CLAIMED.name,
    payload: dict[str, Any] | None = None,
    status: str = "sent",
    read: bool = False,
) -> Notification:
    row = Notification(
        user_id=user.id if user else None,
        channel="push",
        template=template,
        payload=payload if payload is not None else {"contractor": "Obi", "milestone": "Foundation"},
        status=status,
    )
    row.created_at = T0 + timedelta(minutes=minutes)
    row.read_at = T0 if read else None
    session.add(row)
    await session.flush()
    return row


async def test_lists_my_notifications_newest_first_with_the_words_i_saw(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    me = await make_user(db_session)
    older = await add(db_session, me, minutes=0, payload={"contractor": "Obi", "milestone": "Foundation"})
    newer = await add(db_session, me, minutes=5, payload={"contractor": "Obi", "milestone": "Roofing"})
    response = await client.get("/api/v1/me/notifications", headers=auth(me))
    assert response.status_code == 200, response.text
    body = response.json()
    assert [i["id"] for i in body["items"]] == [str(newer.id), str(older.id)]
    first = body["items"][0]
    assert first["title"] == "Milestone claimed"
    assert first["text"] == "Obi says 'Roofing' is done."
    assert first["template"] == "test.feed_claimed"
    assert first["read_at"] is None
    assert body["next_cursor"] is None


async def test_an_item_never_carries_the_raw_payload(client: AsyncClient, db_session: AsyncSession) -> None:
    me = await make_user(db_session)
    await add(db_session, me, payload={"contractor": "Obi", "milestone": "Foundation", "_key": "secret-key"})
    item = (await client.get("/api/v1/me/notifications", headers=auth(me))).json()["items"][0]
    assert set(item) == {"id", "template", "title", "text", "created_at", "read_at"}
    assert "secret-key" not in str(item)


async def test_only_my_own_notifications_are_listed(client: AsyncClient, db_session: AsyncSession) -> None:
    me = await make_user(db_session)
    someone = await make_user(db_session)
    mine = await add(db_session, me)
    await add(db_session, someone)
    items = (await client.get("/api/v1/me/notifications", headers=auth(me))).json()["items"]
    assert [i["id"] for i in items] == [str(mine.id)]


async def test_unread_count_covers_everything_not_just_the_page(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    me = await make_user(db_session)
    for minute in range(5):
        await add(db_session, me, minutes=minute, read=minute == 0)  # 4 unread, 1 read
    body = (await client.get("/api/v1/me/notifications?limit=2", headers=auth(me))).json()
    assert len(body["items"]) == 2
    assert body["unread_count"] == 4


async def test_pages_follow_the_cursor_without_repeats(client: AsyncClient, db_session: AsyncSession) -> None:
    me = await make_user(db_session)
    rows = [await add(db_session, me, minutes=m) for m in range(5)]
    seen: list[str] = []
    cursor: str | None = None
    for _ in range(5):
        url = "/api/v1/me/notifications?limit=2" + (f"&cursor={cursor}" if cursor else "")
        body = (await client.get(url, headers=auth(me))).json()
        seen += [i["id"] for i in body["items"]]
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert seen == [str(r.id) for r in reversed(rows)]


async def test_a_bad_cursor_is_422(client: AsyncClient, db_session: AsyncSession) -> None:
    me = await make_user(db_session)
    response = await client.get("/api/v1/me/notifications?cursor=nonsense", headers=auth(me))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_cursor"


async def test_a_message_that_failed_on_every_channel_is_still_listed(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    me = await make_user(db_session)
    await add(db_session, me, status="failed")
    items = (await client.get("/api/v1/me/notifications", headers=auth(me))).json()["items"]
    assert len(items) == 1


async def test_login_codes_are_never_in_the_feed(client: AsyncClient, db_session: AsyncSession) -> None:
    me = await make_user(db_session)
    code = await add(db_session, me, template=LOGIN_CODE.name, payload={"code": "123456"})
    body = (await client.get("/api/v1/me/notifications", headers=auth(me))).json()
    assert body["items"] == []
    assert body["unread_count"] == 0
    response = await client.post(f"/api/v1/me/notifications/{code.id}/read", headers=auth(me))
    assert response.status_code == 404


async def test_an_unknown_template_gets_a_generic_line_not_the_payload(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    me = await make_user(db_session)
    await add(db_session, me, template="gone.template", payload={"secret": "do-not-show"})
    item = (await client.get("/api/v1/me/notifications", headers=auth(me))).json()["items"][0]
    assert item["title"] == "iBackHome"
    assert item["text"] == "You have a new update from iBackHome."
    assert "do-not-show" not in str(item)


async def test_data_that_no_longer_fits_the_template_keeps_the_title(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    me = await make_user(db_session)
    await add(db_session, me, payload={"contractor": "Obi"})  # 'milestone' is missing
    item = (await client.get("/api/v1/me/notifications", headers=auth(me))).json()["items"][0]
    assert item["title"] == "Milestone claimed"
    assert item["text"] == "You have a new update from iBackHome."


async def test_marking_read_sets_the_time_and_lowers_the_unread_count(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    me = await make_user(db_session)
    row = await add(db_session, me)
    response = await client.post(f"/api/v1/me/notifications/{row.id}/read", headers=auth(me))
    assert response.status_code == 200, response.text
    assert response.json()["read_at"] is not None
    body = (await client.get("/api/v1/me/notifications", headers=auth(me))).json()
    assert body["unread_count"] == 0
    assert body["items"][0]["read_at"] is not None


async def test_reading_twice_keeps_the_first_time(client: AsyncClient, db_session: AsyncSession) -> None:
    me = await make_user(db_session)
    row = await add(db_session, me)
    first = (await client.post(f"/api/v1/me/notifications/{row.id}/read", headers=auth(me))).json()
    second = (await client.post(f"/api/v1/me/notifications/{row.id}/read", headers=auth(me))).json()
    assert second["read_at"] == first["read_at"]


async def test_the_idempotency_key_replays_the_saved_answer(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    me = await make_user(db_session)
    row = await add(db_session, me)
    headers = auth(me) | {"Idempotency-Key": "read-1"}
    first = await client.post(f"/api/v1/me/notifications/{row.id}/read", headers=headers)
    second = await client.post(f"/api/v1/me/notifications/{row.id}/read", headers=headers)
    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()


async def test_someone_elses_notification_is_a_404_and_stays_unread(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    me = await make_user(db_session)
    other = await make_user(db_session)
    theirs = await add(db_session, other)
    response = await client.post(f"/api/v1/me/notifications/{theirs.id}/read", headers=auth(me))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "notification_not_found"
    assert theirs.read_at is None


async def test_an_unknown_id_is_a_404(client: AsyncClient, db_session: AsyncSession) -> None:
    me = await make_user(db_session)
    response = await client.post(f"/api/v1/me/notifications/{NO_ID}/read", headers=auth(me))
    assert response.status_code == 404


@pytest.mark.parametrize("role", ["client", "contractor", "supervisor", "supplier", "ops"])
async def test_every_role_has_a_feed(client: AsyncClient, db_session: AsyncSession, role: str) -> None:
    me = await make_user(db_session, role)
    assert (await client.get("/api/v1/me/notifications", headers=auth(me))).status_code == 200


async def test_signed_out_is_401(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/me/notifications")).status_code == 401
    assert (await client.post(f"/api/v1/me/notifications/{NO_ID}/read")).status_code == 401
