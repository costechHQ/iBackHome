"""The weekly report agent. Owner: James.

Spec (AI agents): Celery Beat, Friday 16:00 WAT, per active project; tools get_project, list_milestones,
list_evidence(since), get_ledger(since); output a Markdown draft that the supervisor reviews.

How a report is made, with the spec's guardrails enforced in code:
1. The week's data is read through the REST API with the agent's service token (read routes only).
2. The model writes only the narrative. If it writes any money figure, the narrative is discarded and
   the plain data summary is used instead ("failures fall back to a plain data summary").
3. The money section is built here from the ledger data, never by the model.
4. The model cites photos as [evidence:<id>]; only ids the evidence route returned are kept.

Routes that are not on main yet answer 404 and are reported as "not available yet":
- GET /projects/{id}/milestones (Lilian), /evidence (Abigail), /ledger (Gabriel).
"""

import json
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service as users
from app.core.errors import AppError
from app.features.agents import llm, runtime
from app.features.agents import service as agents
from app.features.reports import service as reports
from app.features.reports.models import Report

log = logging.getLogger(__name__)

AGENT_NAME = "report"
PROJECT_PATH = "/api/v1/projects/{project_id}"

GET_PROJECT = runtime.AgentTool(
    "get_project",
    "The project: title, address, status, budget and site.",
    "GET",
    PROJECT_PATH,
    {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
)
GET_BOQ = runtime.AgentTool(
    "get_boq",
    "The bill of quantities grouped by milestone.",
    "GET",
    PROJECT_PATH + "/boq",
    {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
)
LIST_MILESTONES = runtime.AgentTool(
    "list_milestones",
    "The project's milestones and their status.",
    "GET",
    PROJECT_PATH + "/milestones",
    {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
)
_SINCE = {
    "type": "object",
    "properties": {"project_id": {"type": "string"}, "since": {"type": "string", "description": "ISO date"}},
    "required": ["project_id"],
}
LIST_EVIDENCE = runtime.AgentTool(
    "list_evidence",
    "Accepted site photos and videos since a date.",
    "GET",
    PROJECT_PATH + "/evidence",
    _SINCE,
)
GET_LEDGER = runtime.AgentTool(
    "get_ledger", "Money in and out of escrow since a date.", "GET", PROJECT_PATH + "/ledger", _SINCE
)
TOOLS = (GET_PROJECT, GET_BOQ, LIST_MILESTONES, LIST_EVIDENCE, GET_LEDGER)
ROUTES = [t.route for t in TOOLS]  # all GETs; agents.service refuses any money route anyway

SYSTEM_PROMPT = """You write the weekly progress report for a family abroad building a house in Enugu.
Write 2-4 short Markdown paragraphs under the heading "## This week": what was built, what was
verified on site, what is next. Plain, warm, factual English. Only use facts from the data given or
from your tools.
Never write any amount of money, price, cost, balance, currency or number of naira/kobo: the money
section is added separately from the escrow ledger.
When a sentence relies on a photo or video, cite it as [evidence:<id>] using ids from the evidence data.
If something is not available yet, say so briefly instead of guessing."""

# Any money figure or currency word in the model's text. Deliberately broad: a false alarm only means
# the plain summary is used; a miss would put a model-written amount in front of a client.
_MONEY = re.compile(
    r"[₦$£€]|\b(NGN|USD|GBP|EUR|naira|kobo|dollars?|pounds?|euros?)\b|\bN\s?\d[\d,.]*\b|\b\d{1,3}(,\d{3})+\b",
    re.IGNORECASE,
)
_CITATION = re.compile(r"\[evidence:([0-9a-fA-F-]{36})\]")
_SYMBOLS = {"NGN": "₦", "USD": "$", "GBP": "£", "EUR": "€"}


def format_minor(amount_minor: int, currency: str) -> str:
    """Integer minor units as money text, e.g. 4500000 NGN -> ₦45,000.00. No floats anywhere."""
    sign = "-" if amount_minor < 0 else ""
    major, minor = divmod(abs(amount_minor), 100)
    symbol = _SYMBOLS.get(currency.upper())
    number = f"{major:,}.{minor:02d}"
    return f"{sign}{symbol}{number}" if symbol else f"{sign}{number} {currency.upper()}"


@dataclass
class WeekData:
    project: dict[str, Any] | None
    milestones: list[dict[str, Any]] | None
    evidence: list[dict[str, Any]] | None
    ledger: list[dict[str, Any]] | None

    @property
    def evidence_ids(self) -> list[str]:
        return [str(e["id"]) for e in self.evidence or [] if e.get("id")]


def _items(body: Any) -> list[dict[str, Any]]:
    """A list route's rows, whether it returns a bare list or a page ({"items": [...]})."""
    rows = body.get("items", []) if isinstance(body, dict) else body
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


async def gather(caller: runtime.ToolCaller, project_id: uuid.UUID, week_start: date) -> WeekData:
    """The week's data, read through the API. A route that isn't there (yet) gives None."""
    since = week_start.isoformat()

    async def read(tool: runtime.AgentTool, **params: Any) -> Any:
        path = tool.path.format(project_id=project_id)
        status, body = await caller(tool.method, path, params)
        if status == 200:
            return body
        log.info("report agent: %s answered %s", tool.route, status)
        return None

    project = await read(GET_PROJECT)
    milestones = await read(LIST_MILESTONES)
    evidence = await read(LIST_EVIDENCE, since=since)
    ledger = await read(GET_LEDGER, since=since)
    return WeekData(
        project=project if isinstance(project, dict) else None,
        milestones=None if milestones is None else _items(milestones),
        evidence=None if evidence is None else _items(evidence),
        ledger=None if ledger is None else _in_week(_items(ledger), week_start),
    )


def _in_week(entries: list[dict[str, Any]], week_start: date) -> list[dict[str, Any]]:
    start = datetime.combine(week_start, time.min).isoformat()
    end = datetime.combine(week_start + timedelta(days=7), time.min).isoformat()
    return [e for e in entries if not e.get("created_at") or start <= str(e["created_at"])[:19] < end]


def money_section(ledger: list[dict[str, Any]] | None) -> str:
    """The money part of the report, built only from ledger rows (spec guardrail)."""
    lines = ["## Money this week (from the escrow ledger)", ""]
    if ledger is None:
        return "\n".join([*lines, "The escrow ledger isn't available in reports yet."])
    if not ledger:
        return "\n".join([*lines, "No money moved this week."])
    lines += ["| Date | Account | Direction | Amount |", "| --- | --- | --- | --- |"]
    totals: dict[tuple[str, str], int] = {}
    for entry in ledger:
        amount, currency = int(entry["amount_minor"]), str(entry["currency"])
        direction = str(entry.get("direction", ""))
        totals[(direction, currency)] = totals.get((direction, currency), 0) + amount
        day = str(entry.get("created_at", ""))[:10]
        lines.append(
            f"| {day} | {entry.get('account', '')} | {direction} | {format_minor(amount, currency)} |"
        )
    lines.append("")
    for (direction, currency), total in sorted(totals.items()):
        lines.append(f"- Total {direction or 'entries'}: {format_minor(total, currency)}")
    return "\n".join(lines)


def milestones_section(milestones: list[dict[str, Any]] | None) -> str:
    lines = ["## Milestones", ""]
    if milestones is None:
        return "\n".join([*lines, "Milestone details aren't available in reports yet."])
    if not milestones:
        return "\n".join([*lines, "No milestones yet."])
    lines += ["| # | Milestone | Status |", "| --- | --- | --- |"]
    for m in sorted(milestones, key=lambda m: int(m.get("sequence", 0))):
        lines.append(f"| {m.get('sequence', '')} | {m.get('name', '')} | {m.get('status', '')} |")
    return "\n".join(lines)


def plain_summary(data: WeekData) -> str:
    """The fallback narrative: facts only, no model involved."""
    status = (data.project or {}).get("status", "unknown")
    photos = "not available yet" if data.evidence is None else str(len(data.evidence))
    return (
        "## This week\n\n"
        f"Project status: **{status}**. New verified photos and videos this week: {photos}.\n\n"
        "_This summary was produced from the project's data because the written report could not be "
        "generated this week._"
    )


def check_narrative(text: str | None, allowed_evidence: list[str]) -> tuple[str, list[str]] | None:
    """The model's narrative with only real citations kept, or None if it can't be used."""
    if not text or not text.strip() or _MONEY.search(text):
        return None
    allowed = {e.lower() for e in allowed_evidence}
    cited: list[str] = []

    def keep(match: re.Match[str]) -> str:
        evidence_id = match.group(1).lower()
        if evidence_id not in allowed:
            return ""
        if evidence_id not in cited:
            cited.append(evidence_id)
        return f"[photo {cited.index(evidence_id) + 1}]"

    narrative = _CITATION.sub(keep, text).strip()
    if not narrative.startswith("## "):
        narrative = "## This week\n\n" + narrative
    return narrative, cited


def compose(narrative: str, cited: list[str], data: WeekData) -> str:
    parts = [narrative, milestones_section(data.milestones), money_section(data.ledger)]
    if cited:
        parts.append("## Photos cited\n\n" + "\n".join(f"{i}. `{e}`" for i, e in enumerate(cited, 1)))
    return "\n\n".join(parts) + "\n"


def _prompt(project_id: uuid.UUID, week_start: date, data: WeekData) -> str:
    facts = {
        "project_id": str(project_id),
        "week": f"{week_start.isoformat()} to {(week_start + timedelta(days=6)).isoformat()}",
        "project": data.project,
        "milestones": data.milestones if data.milestones is not None else "not available yet",
        "evidence": data.evidence if data.evidence is not None else "not available yet",
    }
    # The ledger is deliberately left out: the model must not write about money at all.
    return "Write this week's report. Data:\n" + json.dumps(facts, default=str, indent=1)[:12_000]


@dataclass(frozen=True)
class ReportOutcome:
    report: Report
    used_model: bool  # False when the plain summary was used
    run_id: uuid.UUID


async def generate_weekly_report(
    session: AsyncSession,
    project_id: uuid.UUID,
    week_start: date,
    *,
    caller: runtime.ToolCaller | None = None,
    client: llm.LLMClient | None = None,
) -> ReportOutcome:
    """Draft (or re-draft) one project's report for the week starting `week_start`. Does not commit.

    - 503 agent_user_missing: the report agent's ops user isn't seeded (scripts/seed.py)
    - plus reports.create_draft() refusals (404 project_not_found, 409 report_locked, ...)
    """
    agent_id = agents.agent_user_id(AGENT_NAME)
    if await users.get_user(session, agent_id) is None:
        raise AppError(
            "agent_user_missing", "The report agent's user isn't set up (run scripts/seed.py).", 503
        )
    if caller is None:
        token = agents.create_service_token(AGENT_NAME, ROUTES, user_id=agent_id)
        caller = runtime.ApiToolCaller(headers={"Authorization": f"Bearer {token}"})

    data = await gather(caller, project_id, week_start)
    result = await runtime.run_agent(
        session,
        AGENT_NAME,
        _prompt(project_id, week_start, data),
        TOOLS,
        system=SYSTEM_PROMPT,
        user_id=agent_id,
        caller=caller,
        client=client,
    )
    checked = check_narrative(result.output, data.evidence_ids) if result.ok else None
    if checked is None:
        log.error("report agent fell back to the plain summary for project %s: %s", project_id, result.error)
        cited: list[str] = []
        narrative = plain_summary(data)
    else:
        narrative, cited = checked

    report = await reports.create_draft(
        session,
        project_id,
        week_start,
        compose(narrative, cited, data),
        [uuid.UUID(e) for e in cited],
        actor_id=agent_id,
    )
    return ReportOutcome(report=report, used_model=checked is not None, run_id=result.run_id)
