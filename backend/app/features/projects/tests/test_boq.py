"""The bill of quantities: submit, resubmit, approve, and the milestones an approved BoQ creates.

Day 4 "done when": an approved BoQ creates the right milestones.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.core.errors import AppError
from app.features.milestones import service as milestones
from app.features.projects import service
from app.features.projects.models import BoqApproval, BoqItem, Project
from app.features.projects.schemas import BoqSubmit, Pin, SiteSet
from app.features.projects.tests.factories import (
    FENCE,
    INSIDE,
    audit_entries,
    bearer,
    make_project,
    make_user,
)

# Two milestones, priced in kobo. Foundation: 12.5 m3 x N95,000 + 40 bags x N9,500 = 1,187,500.00 + 380,000.00
BOQ: dict[str, Any] = {
    "milestones": [
        {
            "name": "Foundation",
            "items": [
                {
                    "description": "Concrete 1:2:4, strip foundation",
                    "unit": "m3",
                    "quantity": "12.5",
                    "unit_price_minor": 9_500_000,
                },
                {"description": "Cement, 50 kg", "unit": "bag", "quantity": 40, "unit_price_minor": 950_000},
            ],
        },
        {
            "name": "Blockwork to lintel",
            "items": [
                {
                    "description": "9-inch hollow blocks",
                    "unit": "no.",
                    "quantity": 2000,
                    "unit_price_minor": 65_000,
                },
            ],
        },
    ]
}
FOUNDATION = 118_750_000 + 38_000_000
BLOCKWORK = 2000 * 65_000


@dataclass
class Team:
    project: Project
    client: User
    contractor: User
    ops: User


async def _team(session: AsyncSession, *, site: bool = True) -> Team:
    client = await make_user(session, "client")
    contractor = await make_user(session, "contractor")
    ops = await make_user(session, "ops")
    project = await make_project(session, client=client, contractor=contractor)
    if site:
        await service.set_site(session, client, project.id, SiteSet(location=Pin(**INSIDE), geofence=FENCE))
    return Team(project=project, client=client, contractor=contractor, ops=ops)


@pytest.fixture
async def team(db_session: AsyncSession) -> Team:
    return await _team(db_session)


async def _submit(client: AsyncClient, team: Team, body: dict[str, Any] = BOQ) -> Any:
    return await client.put(
        f"/api/v1/projects/{team.project.id}/boq", json=body, headers=bearer(team.contractor)
    )


async def _approve(client: AsyncClient, team: Team, user: User, **headers: str) -> Any:
    return await client.post(
        f"/api/v1/projects/{team.project.id}/boq/approve", headers=bearer(user) | headers
    )


async def _count(
    session: AsyncSession, model: type[BoqItem] | type[BoqApproval], project_id: uuid.UUID
) -> int:
    count = await session.scalar(
        select(func.count()).select_from(model).where(model.project_id == project_id)
    )
    return int(count or 0)


# --- totals ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("quantity", "unit_price", "total"),
    [
        ("12.5", 9_500_000, 118_750_000),
        ("2.5", 3, 8),  # 7.5 rounds half-up to 8
        ("0.5", 1, 1),  # 0.5 rounds up, not to even
        ("1.333", 3, 4),  # 3.999
        ("1.001", 7, 7),  # 7.007
        ("999999999.999", 10**13, 9_999_999_999_990_000_000_000),
    ],
)
def test_line_total_rounds_half_up(quantity: str, unit_price: int, total: int) -> None:
    assert service.line_total(Decimal(quantity), unit_price) == total


# --- submit --------------------------------------------------------------------------------------


async def test_contractor_submits_and_project_goes_to_review(client: AsyncClient, team: Team) -> None:
    response = await _submit(client, team)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["project_status"] == "boq_review"
    assert [(m["sequence"], m["name"], m["amount_minor"]) for m in body["milestones"]] == [
        (1, "Foundation", FOUNDATION),
        (2, "Blockwork to lintel", BLOCKWORK),
    ]
    assert body["boq_total_minor"] == FOUNDATION + BLOCKWORK
    assert body["milestones"][0]["items"][0]["total_minor"] == 118_750_000
    assert body["milestones"][0]["items"][0]["quantity"] == "12.500"
    assert [line["line_no"] for line in body["milestones"][0]["items"]] == [1, 2]
    assert body["approvals"] == []
    assert body["approvals_missing"] == ["client", "contractor", "ops"]
    assert all(m["milestone_id"] is None for m in body["milestones"])


async def test_submit_is_audited(db_session: AsyncSession, client: AsyncClient, team: Team) -> None:
    await _submit(client, team)
    actions = [e.action for e in await audit_entries(db_session, team.project.id)]
    assert "project.boq_review" in actions
    [entry] = [e for e in await audit_entries(db_session, team.project.id) if e.action == "boq.submitted"]
    assert entry.actor_id == team.contractor.id
    assert entry.before is None
    assert entry.after is not None and entry.after["boq_total_minor"] == FOUNDATION + BLOCKWORK


async def test_matching_total_is_accepted_and_wrong_total_is_422(client: AsyncClient, team: Team) -> None:
    line = {"description": "Sand", "unit": "tonne", "quantity": "2.5", "unit_price_minor": 3}
    ok = {"milestones": [{"name": "Foundation", "items": [line | {"total_minor": 8}]}]}
    assert (await _submit(client, team, ok)).status_code == 200

    wrong = {"milestones": [{"name": "Foundation", "items": [line | {"total_minor": 7}]}]}
    response = await _submit(client, team, wrong)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "boq_total_mismatch"
    assert "should be 8" in response.json()["error"]["message"]


async def test_line_rounding_to_zero_is_422(client: AsyncClient, team: Team) -> None:
    tiny = {"description": "Nail", "unit": "g", "quantity": "0.001", "unit_price_minor": 1}
    response = await _submit(client, team, {"milestones": [{"name": "Roofing", "items": [tiny]}]})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "boq_line_total_zero"


@pytest.mark.parametrize(
    "line",
    [
        {"quantity": "1.2345"},  # more than 3 decimal places
        {"quantity": 0},
        {"quantity": "-1"},
        {"unit_price_minor": 100.0},  # money is never a float
        {"unit_price_minor": 0},
        {"unit_price_minor": "100"},
        {"description": "  "},
        {"unit": ""},
        {"total_minor": 1.5},
    ],
)
async def test_invalid_line_is_422(client: AsyncClient, team: Team, line: dict[str, Any]) -> None:
    base = {"description": "Sand", "unit": "tonne", "quantity": "2", "unit_price_minor": 100}
    response = await _submit(client, team, {"milestones": [{"name": "Foundation", "items": [base | line]}]})
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize(
    "body", [{"milestones": []}, {"milestones": [{"name": "Foundation", "items": []}]}, {}]
)
async def test_empty_boq_is_422(client: AsyncClient, team: Team, body: dict[str, Any]) -> None:
    assert (await _submit(client, team, body)).status_code == 422


async def test_too_many_milestones_or_lines_is_422(client: AsyncClient, team: Team) -> None:
    line = {"description": "Item", "unit": "no.", "quantity": 1, "unit_price_minor": 100}
    too_many = {"milestones": [{"name": f"Stage {i}", "items": [line]} for i in range(21)]}
    response = await _submit(client, team, too_many)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "too_many_milestones"

    lines = {"milestones": [{"name": f"Stage {i}", "items": [line] * 200} for i in range(3)]}
    response = await _submit(client, team, lines)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "too_many_boq_lines"


async def test_over_budget_is_allowed_and_shows_both(client: AsyncClient, team: Team) -> None:
    big = {
        "description": "Everything",
        "unit": "lot",
        "quantity": 1,
        "unit_price_minor": team.project.budget_minor + 1,
    }
    body = (await _submit(client, team, {"milestones": [{"name": "All", "items": [big]}]})).json()
    assert body["boq_total_minor"] == team.project.budget_minor + 1
    assert body["budget_minor"] == team.project.budget_minor


@pytest.mark.parametrize(
    ("who", "code"),
    [("client", "forbidden_role"), ("ops", "forbidden_role"), ("supervisor", "forbidden_role")],
)
async def test_only_contractors_submit(
    client: AsyncClient, db_session: AsyncSession, team: Team, who: str, code: str
) -> None:
    user = team.client if who == "client" else team.ops if who == "ops" else await make_user(db_session, who)
    response = await client.put(f"/api/v1/projects/{team.project.id}/boq", json=BOQ, headers=bearer(user))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == code


async def test_another_projects_contractor_cannot_submit(
    client: AsyncClient, db_session: AsyncSession, team: Team
) -> None:
    stranger = await make_user(db_session, "contractor")
    response = await client.put(f"/api/v1/projects/{team.project.id}/boq", json=BOQ, headers=bearer(stranger))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_project_member"


async def test_resubmitting_in_review_replaces_lines_and_clears_approvals(
    client: AsyncClient, db_session: AsyncSession, team: Team
) -> None:
    await _submit(client, team)
    assert (await _approve(client, team, team.client)).status_code == 200
    assert (await _approve(client, team, team.ops)).status_code == 200

    smaller = {"milestones": [{"name": "Foundation", "items": [BOQ["milestones"][0]["items"][1]]}]}
    body = (await _submit(client, team, smaller)).json()
    assert body["project_status"] == "boq_review"
    assert body["approvals"] == []
    assert body["boq_total_minor"] == 40 * 950_000
    assert await _count(db_session, BoqItem, team.project.id) == 1
    assert await _count(db_session, BoqApproval, team.project.id) == 0

    resubmitted = [e for e in await audit_entries(db_session, team.project.id) if e.action == "boq.submitted"]
    latest = max(resubmitted, key=lambda e: e.at)
    assert latest.before is not None
    assert latest.before["boq_total_minor"] == FOUNDATION + BLOCKWORK
    assert sorted(latest.before["approvals"]) == ["client", "ops"]


# --- approve -------------------------------------------------------------------------------------


async def test_three_approvals_create_the_right_milestones(
    client: AsyncClient, db_session: AsyncSession, team: Team
) -> None:
    """The Day 4 "done when"."""
    await _submit(client, team)
    for user in (team.client, team.contractor):
        body = (await _approve(client, team, user)).json()
        assert body["project_status"] == "boq_review"
    body = (await _approve(client, team, team.ops)).json()
    assert body["project_status"] == "active"
    assert body["approvals_missing"] == []

    created = await milestones.list_for_project(db_session, team.project.id)
    assert [(m.sequence, m.name, m.amount_minor, m.currency, m.status.value) for m in created] == [
        (1, "Foundation", FOUNDATION, "NGN", "pending"),
        (2, "Blockwork to lintel", BLOCKWORK, "NGN", "pending"),
    ]
    # Every BoQ line now points at the milestone created for its group.
    assert [m["milestone_id"] for m in body["milestones"]] == [str(m.id) for m in created]
    items = (await db_session.scalars(select(BoqItem).where(BoqItem.project_id == team.project.id))).all()
    by_sequence = {m.sequence: m.id for m in created}
    assert all(item.milestone_id == by_sequence[item.milestone_sequence] for item in items)
    # Money adds up: the milestones total the BoQ.
    assert sum(m.amount_minor for m in created) == body["boq_total_minor"]

    project = await service.get_project(db_session, team.project.id)
    assert project.status == "active"


async def test_approval_order_does_not_matter(
    client: AsyncClient, db_session: AsyncSession, team: Team
) -> None:
    await _submit(client, team)
    for user in (team.ops, team.contractor, team.client):
        await _approve(client, team, user)
    assert len(await milestones.list_for_project(db_session, team.project.id)) == 2


async def test_approvals_and_activation_are_audited(
    client: AsyncClient, db_session: AsyncSession, team: Team
) -> None:
    await _submit(client, team)
    for user in (team.client, team.contractor, team.ops):
        await _approve(client, team, user)
    entries = await audit_entries(db_session, team.project.id)
    approved = [e for e in entries if e.action == "boq.approved"]
    assert {e.actor_id for e in approved} == {team.client.id, team.contractor.id, team.ops.id}
    [active] = [e for e in entries if e.action == "project.active"]
    assert active.actor_id is None and active.after is not None and active.after["actor_role"] == "system"
    created = await milestones.list_for_project(db_session, team.project.id)
    assert created  # milestone creation itself is Lilian's; the project change is audited here


async def test_final_approval_without_a_site_is_409_and_saves_nothing(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    team = await _team(db_session, site=False)
    await _submit(client, team)
    await _approve(client, team, team.client)
    await _approve(client, team, team.contractor)
    response = await _approve(client, team, team.ops)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "site_not_set"
    assert await _count(db_session, BoqApproval, team.project.id) == 2
    assert (await service.get_project(db_session, team.project.id)).status == "boq_review"
    assert await milestones.list_for_project(db_session, team.project.id) == []


async def test_same_role_cannot_approve_twice(
    client: AsyncClient, db_session: AsyncSession, team: Team
) -> None:
    await _submit(client, team)
    assert (await _approve(client, team, team.ops)).status_code == 200
    second_ops = await make_user(db_session, "ops")
    for user in (team.ops, second_ops):
        response = await _approve(client, team, user)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "boq_already_approved"


async def test_approving_without_a_boq_in_review_is_409(client: AsyncClient, team: Team) -> None:
    response = await _approve(client, team, team.client)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "boq_not_in_review"


@pytest.mark.parametrize(
    ("who", "status", "code"),
    [
        ("supervisor", 403, "forbidden_role"),
        ("supplier", 403, "forbidden_role"),
        ("outsider", 403, "not_project_member"),
    ],
)
async def test_who_cannot_approve(
    client: AsyncClient, db_session: AsyncSession, team: Team, who: str, status: int, code: str
) -> None:
    await _submit(client, team)
    user = await make_user(db_session, "client" if who == "outsider" else who)
    response = await _approve(client, team, user)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


async def test_after_activation_the_boq_is_locked(client: AsyncClient, team: Team) -> None:
    await _submit(client, team)
    for user in (team.client, team.contractor, team.ops):
        await _approve(client, team, user)
    response = await _submit(client, team)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "boq_locked"
    response = await _approve(client, team, team.client)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "boq_not_in_review"


async def test_approve_with_the_same_idempotency_key_replays(
    client: AsyncClient, db_session: AsyncSession, team: Team
) -> None:
    await _submit(client, team)
    first = await _approve(client, team, team.client, **{"Idempotency-Key": "approve-1"})
    second = await _approve(client, team, team.client, **{"Idempotency-Key": "approve-1"})
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert await _count(db_session, BoqApproval, team.project.id) == 1


async def test_submit_with_the_same_idempotency_key_replays(
    client: AsyncClient, db_session: AsyncSession, team: Team
) -> None:
    headers = bearer(team.contractor) | {"Idempotency-Key": "boq-1"}
    url = f"/api/v1/projects/{team.project.id}/boq"
    first = await client.put(url, json=BOQ, headers=headers)
    second = await client.put(url, json=BOQ, headers=headers)
    assert first.json() == second.json()
    submitted = [e for e in await audit_entries(db_session, team.project.id) if e.action == "boq.submitted"]
    assert len(submitted) == 1


async def test_service_checks_roles_itself(db_session: AsyncSession, team: Team) -> None:
    """The rules live in service.py, so a new route can't skip them."""
    with pytest.raises(AppError) as caught:
        await service.submit_boq(db_session, team.client, team.project.id, BoqSubmit.model_validate(BOQ))
    assert caught.value.code == "forbidden_role"
    supervisor = await make_user(db_session, "supervisor")
    with pytest.raises(AppError) as caught:
        await service.approve_boq(db_session, supervisor, team.project.id)
    assert caught.value.code == "forbidden_role"


# --- read ----------------------------------------------------------------------------------------


async def test_members_read_the_boq_and_outsiders_get_403(
    client: AsyncClient, db_session: AsyncSession, team: Team
) -> None:
    url = f"/api/v1/projects/{team.project.id}/boq"
    empty = (await client.get(url, headers=bearer(team.client))).json()
    assert empty["milestones"] == [] and empty["boq_total_minor"] == 0

    await _submit(client, team)
    for user in (team.client, team.contractor, team.ops):
        response = await client.get(url, headers=bearer(user))
        assert response.status_code == 200
        assert response.json()["boq_total_minor"] == FOUNDATION + BLOCKWORK
    outsider = await make_user(db_session, "contractor")
    response = await client.get(url, headers=bearer(outsider))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_project_member"
    assert (await client.get(url)).status_code == 401


async def test_total_above_the_cap_is_422(client: AsyncClient, team: Team) -> None:
    huge = {"description": "Land", "unit": "plot", "quantity": "999999999.999", "unit_price_minor": 10**13}
    response = await _submit(client, team, {"milestones": [{"name": "All", "items": [huge]}]})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "boq_total_too_large"
