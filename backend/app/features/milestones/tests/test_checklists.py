"""Checklist templates: ops write one per kind of milestone, each new milestone gets a copy."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.service import search
from app.features.milestones import service
from app.features.milestones.schemas import DEFAULT_CHECKLIST, ChecklistTemplateIn, MilestoneGroup
from app.features.milestones.tests.factories import active_project, bearer, make_project, make_user

FOUNDATION = ["Trench depth as drawn", "Reinforcement tied and spaced", "Concrete poured and cured"]
URL = "/api/v1/checklist-templates"


async def ops_user(session: AsyncSession) -> Any:
    return await make_user(session, "ops")


async def make_milestones(session: AsyncSession, *names: str) -> list[Any]:
    project = await make_project(session)
    return await service.create_for_project(
        session, project.id, [MilestoneGroup(name=n, amount_minor=1_000) for n in names], "NGN"
    )


def template(name: str, items: list[str]) -> ChecklistTemplateIn:
    return ChecklistTemplateIn(milestone_name=name, items=items)


# --- copying into new milestones ---------------------------------------------------------------


async def test_without_a_template_a_milestone_gets_the_generic_default(db_session: AsyncSession) -> None:
    [foundation] = await make_milestones(db_session, "Foundation")
    assert foundation.checklist == list(DEFAULT_CHECKLIST)
    assert service.checklist_of(foundation) == list(DEFAULT_CHECKLIST)


async def test_a_template_is_copied_into_the_milestones_with_that_name(db_session: AsyncSession) -> None:
    ops = await ops_user(db_session)
    await service.set_template(db_session, ops, template("Foundation", FOUNDATION))
    foundation, roofing = await make_milestones(db_session, "Foundation", "Roofing")
    assert foundation.checklist == FOUNDATION
    assert roofing.checklist == list(DEFAULT_CHECKLIST)  # no template for it: the default


@pytest.mark.parametrize("name", ["foundation", "  FOUNDATION ", "Foundation", "foundation   "])
async def test_a_name_finds_its_template_whatever_the_case_and_spacing(
    db_session: AsyncSession, name: str
) -> None:
    ops = await ops_user(db_session)
    await service.set_template(db_session, ops, template("Foundation", FOUNDATION))
    [milestone] = await make_milestones(db_session, name)
    assert milestone.checklist == FOUNDATION


async def test_editing_a_template_never_changes_a_milestone_that_already_exists(
    db_session: AsyncSession,
) -> None:
    ops = await ops_user(db_session)
    await service.set_template(db_session, ops, template("Foundation", FOUNDATION))
    [existing] = await make_milestones(db_session, "Foundation")
    await service.set_template(db_session, ops, template("Foundation", ["Only one item now"]))
    assert existing.checklist == FOUNDATION  # its own copy
    [fresh] = await make_milestones(db_session, "Foundation")
    assert fresh.checklist == ["Only one item now"]


async def test_the_copy_is_its_own_list(db_session: AsyncSession) -> None:
    ops = await ops_user(db_session)
    row = await service.set_template(db_session, ops, template("Foundation", FOUNDATION))
    [milestone] = await make_milestones(db_session, "Foundation")
    assert milestone.checklist == row.items
    assert milestone.checklist is not row.items


async def test_a_milestone_made_before_templates_existed_reads_as_the_default(
    db_session: AsyncSession,
) -> None:
    [old] = await make_milestones(db_session, "Foundation")
    old.checklist = None
    assert service.checklist_of(old) == list(DEFAULT_CHECKLIST)


# --- ops write them ----------------------------------------------------------------------------


async def test_ops_write_and_read_templates(client: AsyncClient, db_session: AsyncSession) -> None:
    ops = await ops_user(db_session)
    put = await client.put(
        URL, json={"milestone_name": "Foundation", "items": FOUNDATION}, headers=bearer(ops)
    )
    assert put.status_code == 200, put.text
    assert put.json()["milestone_name"] == "Foundation"
    assert put.json()["items"] == FOUNDATION
    assert put.json()["updated_by"] == str(ops.id)
    listed = (await client.get(URL, headers=bearer(ops))).json()
    assert [t["milestone_name"] for t in listed] == ["Foundation"]


async def test_writing_again_replaces_the_template_and_keeps_one_row(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ops = await ops_user(db_session)
    await client.put(URL, json={"milestone_name": "Foundation", "items": FOUNDATION}, headers=bearer(ops))
    await client.put(URL, json={"milestone_name": " foundation ", "items": ["New item"]}, headers=bearer(ops))
    listed = (await client.get(URL, headers=bearer(ops))).json()
    assert len(listed) == 1
    assert listed[0]["items"] == ["New item"]
    assert listed[0]["milestone_name"] == "foundation"  # as ops last wrote it


async def test_spacing_inside_items_and_names_is_tidied(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ops = await ops_user(db_session)
    body = {"milestone_name": "  Blockwork   to lintel ", "items": ["  Walls   plumb  ", "Lintel  level"]}
    out = (await client.put(URL, json=body, headers=bearer(ops))).json()
    assert out["milestone_name"] == "Blockwork to lintel"
    assert out["items"] == ["Walls plumb", "Lintel level"]


async def test_a_change_is_audited_with_the_old_and_new_list_and_a_repeat_is_not(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ops = await ops_user(db_session)
    first = (
        await client.put(URL, json={"milestone_name": "Roofing", "items": ["A"]}, headers=bearer(ops))
    ).json()
    await client.put(
        URL, json={"milestone_name": "Roofing", "items": ["A"]}, headers=bearer(ops)
    )  # same again
    await client.put(URL, json={"milestone_name": "Roofing", "items": ["A", "B"]}, headers=bearer(ops))
    row = await service.templates_by_key(db_session, ["Roofing"])
    entries, _ = await search(db_session, object_id=row["roofing"].id, action="checklist_template.set")
    assert len(entries) == 2  # created, then changed; the repeat wrote nothing
    newest = entries[0]
    assert newest.actor_id == ops.id
    assert newest.before is not None and newest.after is not None
    assert newest.before["items"] == ["A"]
    assert newest.after["items"] == ["A", "B"]
    assert first["items"] == ["A"]


async def test_the_idempotency_key_replays_the_answer(client: AsyncClient, db_session: AsyncSession) -> None:
    ops = await ops_user(db_session)
    headers = bearer(ops) | {"Idempotency-Key": "tpl-1"}
    body = {"milestone_name": "Roofing", "items": ["A"]}
    first = await client.put(URL, json=body, headers=headers)
    second = await client.put(URL, json=body, headers=headers)
    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()


@pytest.mark.parametrize("role", ["client", "contractor", "supervisor", "supplier"])
async def test_only_ops_can_read_or_write_templates(
    client: AsyncClient, db_session: AsyncSession, role: str
) -> None:
    someone = await make_user(db_session, role)
    body = {"milestone_name": "Foundation", "items": FOUNDATION}
    put = await client.put(URL, json=body, headers=bearer(someone))
    assert put.status_code == 403
    assert put.json()["error"]["code"] == "forbidden_role"
    assert (await client.get(URL, headers=bearer(someone))).status_code == 403


async def test_signed_out_is_401(client: AsyncClient) -> None:
    assert (await client.get(URL)).status_code == 401
    assert (await client.put(URL, json={"milestone_name": "X", "items": ["A"]})).status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {"milestone_name": "Foundation", "items": []},  # a template needs items
        {"milestone_name": "Foundation", "items": ["A", "   "]},  # no blank item
        {"milestone_name": "Foundation", "items": ["Slab level", "slab LEVEL"]},  # no repeats
        {"milestone_name": "Foundation", "items": ["x" * 201]},  # at most 200 characters
        {"milestone_name": "Foundation", "items": [f"item {i}" for i in range(51)]},  # at most 50 items
        {"milestone_name": "   ", "items": ["A"]},  # a name is needed
        {"milestone_name": "x" * 121, "items": ["A"]},
        {"items": ["A"]},
        {"milestone_name": "Foundation"},
    ],
)
async def test_a_bad_template_is_422(
    client: AsyncClient, db_session: AsyncSession, body: dict[str, Any]
) -> None:
    ops = await ops_user(db_session)
    assert (await client.put(URL, json=body, headers=bearer(ops))).status_code == 422


async def test_fifty_items_of_two_hundred_characters_is_the_limit(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ops = await ops_user(db_session)
    items = [f"{i:02d} " + "x" * 197 for i in range(50)]
    assert (
        await client.put(URL, json={"milestone_name": "Big", "items": items}, headers=bearer(ops))
    ).status_code == 200


# --- what the app reads ------------------------------------------------------------------------


async def test_every_member_reads_the_checklist_with_the_milestones(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ops = await ops_user(db_session)
    await service.set_template(db_session, ops, template("Foundation", FOUNDATION))
    site = await active_project(db_session)  # Foundation, then Roofing
    for viewer in (site.client, site.contractor, site.supervisor, site.ops):
        listed = (
            await client.get(f"/api/v1/projects/{site.project_id}/milestones", headers=bearer(viewer))
        ).json()
        assert listed[0]["name"] == "Foundation"
        assert listed[0]["checklist"] == FOUNDATION
        assert listed[1]["name"] == "Roofing"
        assert listed[1]["checklist"] == list(DEFAULT_CHECKLIST)


async def test_an_older_milestone_with_no_stored_checklist_shows_the_default(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    site = await active_project(db_session)
    site.milestones[0].checklist = None
    await db_session.flush()
    listed = (
        await client.get(f"/api/v1/projects/{site.project_id}/milestones", headers=bearer(site.supervisor))
    ).json()
    assert listed[0]["checklist"] == list(DEFAULT_CHECKLIST)


async def test_someone_not_on_the_project_cannot_read_its_checklists(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    site = await active_project(db_session)
    stranger = await make_user(db_session, "supervisor")
    response = await client.get(f"/api/v1/projects/{site.project_id}/milestones", headers=bearer(stranger))
    assert response.status_code == 403


async def test_a_template_in_one_project_never_reaches_another_projects_existing_milestones(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    older = await active_project(db_session)
    ops = await ops_user(db_session)
    await service.set_template(db_session, ops, template("Foundation", FOUNDATION))
    listed = (
        await client.get(f"/api/v1/projects/{older.project_id}/milestones", headers=bearer(older.supervisor))
    ).json()
    assert listed[0]["checklist"] == list(DEFAULT_CHECKLIST)
