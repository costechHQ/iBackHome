"""scripts/load_checklists.py: ops' checklists from a Markdown file, checked first, saved all or nothing."""

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.service import search
from app.base.users.models import User
from app.features.milestones import service
from app.features.milestones.schemas import MilestoneGroup
from app.features.milestones.tests.factories import make_project, make_user
from scripts import load_checklists as loader

GOOD = """## Foundation
- Trench depth as drawn
- Reinforcement tied and spaced

## Roofing
- Trusses fixed and braced
"""


# --- reading the file ----------------------------------------------------------------------------


def test_headings_and_bullets_become_templates() -> None:
    templates, problems = loader.parse_checklists(GOOD)
    assert problems == []
    assert [(t.milestone_name, t.items) for t in templates] == [
        ("Foundation", ["Trench depth as drawn", "Reinforcement tied and spaced"]),
        ("Roofing", ["Trusses fixed and braced"]),
    ]


@pytest.mark.parametrize("bullet", ["- ", "* ", "+ ", "1. ", "2) ", "10. "])
def test_every_common_bullet_style_works(bullet: str) -> None:
    templates, problems = loader.parse_checklists(f"## Foundation\n{bullet}Slab level\n")
    assert problems == []
    assert templates[0].items == ["Slab level"]


@pytest.mark.parametrize(
    "heading", ["# Foundation", "## Foundation", "### Foundation", "##   Foundation  ", "## Foundation ##"]
)
def test_any_heading_level_works(heading: str) -> None:
    templates, problems = loader.parse_checklists(f"{heading}\n- Slab level\n")
    assert problems == []
    assert templates[0].milestone_name == "Foundation"


def test_windows_line_endings_a_byte_order_mark_and_blank_lines_are_fine() -> None:
    text = "﻿## Foundation\r\n\r\n- Slab level\r\n\r\n\r\n- Walls plumb\r\n"
    templates, problems = loader.parse_checklists(text)
    assert problems == []
    assert templates[0].items == ["Slab level", "Walls plumb"]


def test_spacing_is_tidied_the_same_way_as_the_api_does() -> None:
    templates, _ = loader.parse_checklists("##   Blockwork   to lintel\n-   Walls    plumb  \n")
    assert templates[0].milestone_name == "Blockwork to lintel"
    assert templates[0].items == ["Walls plumb"]


# --- mistakes are named, not dropped -------------------------------------------------------------


def test_an_item_before_any_heading_is_named_by_line() -> None:
    _, problems = loader.parse_checklists("- Orphan item\n## Foundation\n- Slab level\n")
    assert problems == ["line 1: an item before any heading (start with a '## Milestone name' line)"]


def test_stray_text_is_named_by_line_and_never_silently_ignored() -> None:
    _, problems = loader.parse_checklists("## Foundation\nSlab level without a dash\n- Walls plumb\n")
    assert len(problems) == 1
    assert problems[0].startswith("line 2: expected a '## heading' or a '- item', got: Slab level")


def test_a_dash_with_nothing_after_it_is_a_mistake() -> None:
    _, problems = loader.parse_checklists("## Foundation\n-\n- Slab level\n")
    assert any(p.startswith("line 2:") for p in problems)


def test_a_heading_with_no_items_is_a_problem() -> None:
    _, problems = loader.parse_checklists("## Foundation\n\n## Roofing\n- Trusses fixed\n")
    assert len(problems) == 1
    assert problems[0].startswith("line 1: 'Foundation'")


def test_the_same_milestone_twice_is_a_problem_whatever_the_case() -> None:
    _, problems = loader.parse_checklists("## Foundation\n- A\n\n## foundation  \n- B\n")
    assert problems == ["line 4: 'foundation' is already given on line 1"]


def test_a_repeated_blank_or_too_long_item_is_a_problem_naming_the_milestone() -> None:
    _, repeated = loader.parse_checklists("## Foundation\n- Slab level\n- slab LEVEL\n")
    assert "appears twice" in repeated[0] and "'Foundation'" in repeated[0]
    _, long = loader.parse_checklists(f"## Foundation\n- {'x' * 201}\n")
    assert "at most 200 characters" in long[0]


def test_more_than_fifty_items_is_a_problem() -> None:
    text = "## Foundation\n" + "\n".join(f"- item {i}" for i in range(51))
    _, problems = loader.parse_checklists(text)
    assert len(problems) == 1 and problems[0].startswith("line 1: 'Foundation'")


def test_every_problem_is_listed_at_once_and_good_sections_are_still_read() -> None:
    text = "- orphan\n## Foundation\n- A\n- a\n## Roofing\n- Fine\nstray\n"
    templates, problems = loader.parse_checklists(text)
    assert len(problems) == 3
    assert [t.milestone_name for t in templates] == ["Roofing"]


@pytest.mark.parametrize("text", ["", "   \n\n  \n"])
def test_an_empty_file_is_a_problem_not_a_success(text: str) -> None:
    templates, problems = loader.parse_checklists(text)
    assert templates == []
    assert problems and "no checklists" in problems[0]


# --- checking and saving -------------------------------------------------------------------------


async def make_ops(session: AsyncSession) -> User:
    ops = await make_user(session, "ops")
    return ops


def parsed(text: str = GOOD) -> list:  # type: ignore[type-arg]
    templates, problems = loader.parse_checklists(text)
    assert problems == []
    return templates


async def test_checking_saves_nothing(db_session: AsyncSession) -> None:
    lines = await loader.run(db_session, parsed(), apply=False, acting_as=None)
    assert [line.split(None, 1)[0] for line in lines] == ["Foundation", "Roofing"]
    assert all("new, " in line for line in lines)
    assert await service.list_templates(db_session) == []


async def test_applying_saves_them_against_the_ops_user_and_audits_each(db_session: AsyncSession) -> None:
    ops = await make_ops(db_session)
    lines = await loader.run(db_session, parsed(), apply=True, acting_as=ops.phone)
    assert "new, 2 items" in lines[0] and "new, 1 item" in lines[1]
    saved = {t.milestone_name: t for t in await service.list_templates(db_session)}
    assert saved["Foundation"].items == ["Trench depth as drawn", "Reinforcement tied and spaced"]
    assert saved["Foundation"].updated_by == ops.id
    entries, _ = await search(db_session, object_id=saved["Roofing"].id, action="checklist_template.set")
    assert len(entries) == 1 and entries[0].actor_id == ops.id


async def test_running_it_twice_changes_nothing_the_second_time(db_session: AsyncSession) -> None:
    ops = await make_ops(db_session)
    await loader.run(db_session, parsed(), apply=True, acting_as=ops.phone)
    again = await loader.run(db_session, parsed(), apply=True, acting_as=ops.phone)
    assert all("unchanged" in line for line in again)
    entries, _ = await search(db_session, action="checklist_template.set")
    assert len(entries) == 2  # one per template, from the first run only


async def test_a_changed_list_is_reported_and_replaced(db_session: AsyncSession) -> None:
    ops = await make_ops(db_session)
    await loader.run(db_session, parsed(), apply=True, acting_as=ops.phone)
    lines = await loader.run(
        db_session, parsed("## Foundation\n- Only one now\n"), apply=True, acting_as=ops.phone
    )
    assert "changed, 2 items -> 1" in lines[0]
    saved = {t.milestone_name: t for t in await service.list_templates(db_session)}
    assert saved["Foundation"].items == ["Only one now"]
    assert "Roofing" in saved  # a template not in the file is left alone, never deleted


async def test_checking_a_changed_file_says_what_would_change_and_changes_nothing(
    db_session: AsyncSession,
) -> None:
    ops = await make_ops(db_session)
    await loader.run(db_session, parsed(), apply=True, acting_as=ops.phone)
    lines = await loader.run(
        db_session, parsed("## Foundation\n- Only one now\n"), apply=False, acting_as=None
    )
    assert "changed, 2 items -> 1" in lines[0]
    saved = {t.milestone_name: t for t in await service.list_templates(db_session)}
    assert len(saved["Foundation"].items) == 2


async def test_applying_without_saying_who_is_refused_and_saves_nothing(db_session: AsyncSession) -> None:
    with pytest.raises(SystemExit, match="--as"):
        await loader.run(db_session, parsed(), apply=True, acting_as=None)
    assert await service.list_templates(db_session) == []


async def test_the_user_must_be_an_ops_user_that_exists(db_session: AsyncSession) -> None:
    supervisor = await make_user(db_session, "supervisor")
    with pytest.raises(SystemExit, match="not an ops user"):
        await loader.run(db_session, parsed(), apply=True, acting_as=supervisor.phone)
    with pytest.raises(SystemExit, match="not an ops user"):
        await loader.run(db_session, parsed(), apply=True, acting_as="+2348039999999")
    with pytest.raises(SystemExit, match="--as"):
        await loader.run(db_session, parsed(), apply=True, acting_as="not a number")
    assert await service.list_templates(db_session) == []


async def test_the_ops_user_can_be_given_by_email_or_a_local_phone_number(db_session: AsyncSession) -> None:
    ops = await make_user(db_session, "ops")
    ops.email = "ops.lead@example.com"
    await db_session.flush()
    assert ops.phone is not None
    local = "0" + ops.phone.removeprefix("+234")
    for who in ("ops.lead@example.com", "OPS.Lead@Example.com", local):
        await loader.run(db_session, parsed("## Foundation\n- A\n"), apply=True, acting_as=who)
    saved = await service.list_templates(db_session)
    assert len(saved) == 1 and saved[0].updated_by == ops.id


async def test_new_milestones_then_get_the_loaded_lists(db_session: AsyncSession) -> None:
    ops = await make_ops(db_session)
    await loader.run(db_session, parsed(), apply=True, acting_as=ops.phone)
    project = await make_project(db_session)
    foundation, roofing, other = await service.create_for_project(
        db_session,
        project.id,
        [MilestoneGroup(name=n, amount_minor=1_000) for n in ("Foundation", "roofing", "Finishing")],
        "NGN",
    )
    assert foundation.checklist == ["Trench depth as drawn", "Reinforcement tied and spaced"]
    assert roofing.checklist == ["Trusses fixed and braced"]
    assert (
        other.checklist is not None and "Workmanship is acceptable" in other.checklist
    )  # no template: default


# --- the command line ----------------------------------------------------------------------------


async def test_a_file_with_problems_saves_nothing_and_says_so(capsys: pytest.CaptureFixture[str]) -> None:
    code = await loader.main(
        Path("checklists.md"), "- orphan\n## Foundation\n- A\n", apply=True, acting_as="x"
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "1 problem, nothing saved" in out
    assert "line 1:" in out


async def test_checking_a_bad_file_says_nothing_was_checked_as_ok(capsys: pytest.CaptureFixture[str]) -> None:
    code = await loader.main(Path("c.md"), "stray text\n", apply=False, acting_as=None)
    assert code == 1
    assert "nothing checked" in capsys.readouterr().out


def test_the_plural_helper() -> None:
    assert loader.plural(1, "problem") == "1 problem"
    assert loader.plural(2, "checklist") == "2 checklists"
