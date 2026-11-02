"""Load ops' milestone checklists from a plain text file. Owner: James.

The checklist for each kind of milestone (Foundation, Roofing, ...) is ops' to write. This reads them from
a Markdown file and saves them through the same rules as `PUT /checklist-templates`, so every change is
audited and a list is checked the same way (1 to 50 items, at most 200 characters each, no blanks, no
repeats).

The file is just headings and bullets, one heading per kind of milestone:

    ## Foundation
    - First thing the supervisor checks
    - Second thing

    ## Roofing
    - First thing
    - Second thing

A line starting with `#` is a milestone name; a line starting with `-`, `*` or `1.` is an item under it; blank
lines are ignored. Anything else is an error, with its line number, so a typo is never silently dropped.

By default it only CHECKS the file and says what would change. Nothing is saved until `--apply`:

    uv run python scripts/load_checklists.py checklists.md
    uv run python scripts/load_checklists.py checklists.md --apply --as 08030000004

`--as` is the ops user the change is recorded against (their phone number or email). Inside the api container:

    docker compose exec api python scripts/load_checklists.py /app/checklists.md --apply --as <ops phone>

It saves everything or nothing: one bad section stops the whole load. Running it twice is safe (an
unchanged list is left alone). Milestones that already exist keep the checklist they were made with; the new
lists apply to milestones created from now on.
"""

import argparse
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `app` imports when run as a script

from pydantic import ValidationError  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.base.users import service as users  # noqa: E402
from app.base.users.models import Role, User  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.core.errors import AppError  # noqa: E402
from app.features.milestones import service as milestones  # noqa: E402
from app.features.milestones.schemas import ChecklistTemplateIn  # noqa: E402

HEADING = re.compile(r"^#{1,6}\s*(?P<name>.*?)\s*#*\s*$")
BULLET = re.compile(r"^(?:[-*+]|\d+[.)])\s+(?P<item>.*?)\s*$")


def parse_checklists(text: str) -> tuple[list[ChecklistTemplateIn], list[str]]:
    """The templates in the text, and every problem found (each names its line). No problems: safe to save."""
    problems: list[str] = []
    sections: list[tuple[int, str, list[str]]] = []  # (heading line, name, items)
    for number, raw in enumerate(text.lstrip("﻿").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if heading := HEADING.match(line):
            sections.append((number, heading.group("name"), []))
        elif bullet := BULLET.match(line):
            if not sections:
                problems.append(
                    f"line {number}: an item before any heading (start with a '## Milestone name' line)"
                )
            else:
                sections[-1][2].append(bullet.group("item"))
        else:
            problems.append(f"line {number}: expected a '## heading' or a '- item', got: {line[:60]}")

    templates: list[ChecklistTemplateIn] = []
    seen: dict[str, int] = {}
    for number, name, items in sections:
        key = milestones.template_key(name)
        if key in seen:
            problems.append(f"line {number}: '{name}' is already given on line {seen[key]}")
            continue
        seen[key] = number
        try:
            templates.append(ChecklistTemplateIn(milestone_name=name, items=items))
        except ValidationError as exc:
            reasons = "; ".join(sorted({e["msg"].removeprefix("Value error, ") for e in exc.errors()}))
            problems.append(f"line {number}: '{name}': {reasons}")
    if not sections and not problems:
        problems.append("the file has no checklists (nothing starting with '#')")
    return templates, problems


def plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


async def find_ops(session: AsyncSession, identifier: str) -> User:
    """The ops user the changes are recorded against, by phone number or email."""
    try:
        value, channel = users.normalise_identifier(identifier)
    except AppError as exc:
        raise SystemExit(f"--as: {exc.message}") from exc
    column = User.email if channel == "email" else User.phone
    user = await session.scalar(select(User).where(column == value))
    if user is None or user.role != Role.OPS.value:
        raise SystemExit(f"--as: {identifier} is not an ops user.")
    return user


async def run(
    session: AsyncSession, templates: list[ChecklistTemplateIn], *, apply: bool, acting_as: str | None
) -> list[str]:
    """Compare (and with `apply`, save) the templates. Returns one report line each. The caller commits."""
    existing = {t.milestone_key: t for t in await milestones.list_templates(session)}
    ops = await find_ops(session, acting_as) if apply and acting_as else None
    if apply and ops is None:
        raise SystemExit("--apply needs --as <the ops user's phone or email>.")
    lines: list[str] = []
    for data in templates:
        old = existing.get(milestones.template_key(data.milestone_name))
        if old is None:
            verdict = f"new, {plural(len(data.items), 'item')}"
        elif old.items == data.items and old.milestone_name == data.milestone_name:
            verdict = f"unchanged, {plural(len(data.items), 'item')}"
        else:
            verdict = f"changed, {plural(len(old.items), 'item')} -> {len(data.items)}"
        if ops is not None:
            await milestones.set_template(session, ops, data)
        lines.append(f"{data.milestone_name:<30} {verdict}")
    return lines


async def main(path: Path, text: str, *, apply: bool, acting_as: str | None) -> int:
    templates, problems = parse_checklists(text)
    outcome = "saved" if apply else "checked"
    if problems:
        print(f"{path}: {plural(len(problems), 'problem')}, nothing {outcome}:")
        for problem in problems:
            print(f"  {problem}")
        return 1
    async with SessionLocal() as session:
        lines = await run(session, templates, apply=apply, acting_as=acting_as)
        if apply:
            await session.commit()
    print(f"{path}: {plural(len(templates), 'checklist')} {outcome}")
    for line in lines:
        print(f"  {line}")
    if not apply:
        print("Nothing was saved. Run again with --apply --as <ops phone or email> to save.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load ops' milestone checklists from a Markdown file.")
    parser.add_argument(
        "file", type=Path, help="the checklists: '## Milestone name' headings with '- item' bullets"
    )
    parser.add_argument("--apply", action="store_true", help="save them (without this, only check the file)")
    parser.add_argument(
        "--as", dest="acting_as", metavar="OPS", help="the ops user to record the change against"
    )
    args = parser.parse_args()
    if sys.platform == "win32":  # async psycopg can't use Windows' default event loop
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        contents = args.file.read_text(encoding="utf-8")
    except OSError as exc:
        raise SystemExit(f"{args.file}: {exc.strerror or exc}") from exc
    sys.exit(asyncio.run(main(args.file, contents, apply=args.apply, acting_as=args.acting_as)))
