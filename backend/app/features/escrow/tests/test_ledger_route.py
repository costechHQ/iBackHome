"""GET /projects/{id}/ledger: funding, releases and payouts, for the project's client and ops (spec)."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.payments import service as payments_service
from app.features.escrow import service as escrow
from app.features.escrow import tasks as escrow_tasks
from app.features.escrow.tests.factories import FOUNDATION_NGN, Funded, make_active_project, simulated_escrow
from app.features.escrow.tests.release_helpers import (
    add_recipient,
    approve_milestone,
    hold_milestone,
    session_factory,
)
from app.features.projects.tests.factories import bearer, make_user


@pytest.fixture(autouse=True)
def _fresh_escrow(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(escrow, "enqueue_submit_release", lambda release_id: None)
    monkeypatch.setattr(payments_service, "enqueue_send_transfer", lambda payout_id: None)
    simulated_escrow().reset()
    yield
    simulated_escrow().reset()


def url(funded: Funded, **params: str | int) -> str:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"/api/v1/projects/{funded.project.id}/ledger" + (f"?{query}" if query else "")


async def funded_and_released(db_session: AsyncSession) -> Funded:
    funded = await make_active_project(db_session)
    await hold_milestone(db_session, funded.project.id, funded.foundation)
    await approve_milestone(db_session, funded, funded.foundation)
    await add_recipient(db_session, user_id=funded.contractor.id)
    result = await escrow.request_release(db_session, funded.foundation.id, funded.client)
    await escrow_tasks.run_submit_release(session_factory(db_session), result.release_id, retries=0)
    return funded


async def test_client_sees_funding_and_the_release_newest_first(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    funded = await funded_and_released(db_session)
    response = await client.get(url(funded), headers=bearer(funded.client))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["next_cursor"] is None
    p = funded.project.id
    lines = sorted((e["account"], e["direction"], e["amount_minor"]) for e in body["items"])
    assert lines == sorted(
        [
            (f"escrow:{p}:NGN", "debit", FOUNDATION_NGN),  # held
            ("fx_conversion:NGN", "credit", FOUNDATION_NGN),
            ("contractor_payable:NGN", "debit", FOUNDATION_NGN),  # released
            (f"escrow:{p}:NGN", "credit", FOUNDATION_NGN),
        ]
    )
    first = body["items"][0]
    assert set(first) >= {"created_at", "account", "direction", "amount_minor", "currency", "transaction_id"}
    assert isinstance(first["amount_minor"], int)
    times = [e["created_at"] for e in body["items"]]
    assert times == sorted(times, reverse=True)


async def test_ops_sees_any_projects_ledger(client: AsyncClient, db_session: AsyncSession) -> None:
    funded = await funded_and_released(db_session)
    ops = await make_user(db_session, "ops")
    response = await client.get(url(funded), headers=bearer(ops))
    assert response.status_code == 200
    assert len(response.json()["items"]) == 4


async def test_contractor_is_refused(client: AsyncClient, db_session: AsyncSession) -> None:
    funded = await funded_and_released(db_session)
    response = await client.get(url(funded), headers=bearer(funded.contractor))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_project_client"


async def test_another_client_is_refused(client: AsyncClient, db_session: AsyncSession) -> None:
    funded = await funded_and_released(db_session)
    stranger = await make_user(db_session, "client")
    response = await client.get(url(funded), headers=bearer(stranger))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_project_member"


async def test_pages_follow_the_cursor_without_repeats(client: AsyncClient, db_session: AsyncSession) -> None:
    funded = await funded_and_released(db_session)
    first = (await client.get(url(funded, limit=3), headers=bearer(funded.client))).json()
    assert len(first["items"]) == 3 and first["next_cursor"]
    second = (
        await client.get(url(funded, limit=3, cursor=first["next_cursor"]), headers=bearer(funded.client))
    ).json()
    assert len(second["items"]) == 1 and second["next_cursor"] is None
    ids = [e["id"] for e in first["items"] + second["items"]]
    assert len(set(ids)) == 4


async def test_since_and_until_filter_by_time(client: AsyncClient, db_session: AsyncSession) -> None:
    funded = await funded_and_released(db_session)
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).date().isoformat()
    later = await client.get(url(funded, since=tomorrow), headers=bearer(funded.client))
    assert later.status_code == 200 and later.json()["items"] == []
    before = await client.get(url(funded, until=tomorrow), headers=bearer(funded.client))
    assert len(before.json()["items"]) == 4


async def test_bad_cursor_is_422(client: AsyncClient, db_session: AsyncSession) -> None:
    funded = await make_active_project(db_session)
    response = await client.get(url(funded, cursor="nope"), headers=bearer(funded.client))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_cursor"


async def test_needs_a_login(client: AsyncClient, db_session: AsyncSession) -> None:
    funded = await make_active_project(db_session)
    assert (await client.get(url(funded))).status_code == 401
