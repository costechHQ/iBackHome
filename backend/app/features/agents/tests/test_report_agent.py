"""The weekly report agent (report_agent.py). A fake Gemini writes the narrative; needs Postgres."""

import asyncio
import secrets
import uuid
from datetime import date
from typing import Any

import pytest
from google.genai import types
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.core.errors import AppError
from app.features.agents import report_agent as ra
from app.features.agents import service as agents
from app.features.agents.llm import LLMClient, LLMSettings
from app.features.agents.models import AgentRun
from app.features.projects import service as projects
from app.features.projects.models import Project
from app.features.projects.schemas import ProjectCreate
from scripts import seed

MONDAY = date(2026, 10, 12)
PHOTO_A, PHOTO_B, MADE_UP = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
LEDGER: dict[str, Any] = {
    "items": [
        {
            "account": "escrow:project",
            "direction": "credit",
            "amount_minor": 4_500_000_00,
            "currency": "NGN",
            "created_at": "2026-10-13T09:00:00+00:00",
        },
        {
            "account": "escrow:project",
            "direction": "debit",
            "amount_minor": 1_250_000_50,
            "currency": "NGN",
            "created_at": "2026-10-16T15:30:00+00:00",
        },
        {  # last week: must not appear
            "account": "escrow:project",
            "direction": "credit",
            "amount_minor": 99,
            "currency": "NGN",
            "created_at": "2026-10-05T09:00:00+00:00",
        },
    ],
    "next_cursor": None,
}


class FakeModels:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.requests: list[dict[str, Any]] = []

    async def generate_content(self, **request: Any) -> types.GenerateContentResponse:
        self.requests.append(request)
        await asyncio.sleep(0)
        return types.GenerateContentResponse.model_validate(
            {
                "candidates": [{"content": {"role": "model", "parts": [{"text": self.answer}]}}],
                "model_version": "g",
            }
        )


def model(answer: str) -> tuple[LLMClient, FakeModels]:
    models = FakeModels(answer)
    fake = type("FakeGemini", (), {"models": models})()
    fake.aio = fake
    return LLMClient(LLMSettings(llm_api_key="unused", llm_model="g"), client=fake), models


class FakeApi:
    """Answers the report agent's reads like the real routes will (404 for any it doesn't know)."""

    def __init__(self, routes: dict[str, Any]) -> None:
        self.routes = routes
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    async def __call__(self, method: str, path: str, params: dict[str, Any]) -> tuple[int, Any]:
        self.calls.append((method, path, params))
        suffix = path.rsplit("/", 1)[-1]
        key = "project" if len(suffix) == 36 else suffix
        return (200, self.routes[key]) if key in self.routes else (404, {"error": {"code": "not_found"}})


def full_api(project_id: uuid.UUID) -> FakeApi:
    return FakeApi(
        {
            "project": {"id": str(project_id), "title": "Duplex", "status": "active"},
            "milestones": [
                {"sequence": 2, "name": "Lintel", "status": "funded"},
                {"sequence": 1, "name": "Foundation", "status": "released"},
            ],
            "evidence": {"items": [{"id": PHOTO_A}, {"id": PHOTO_B}]},
            "ledger": LEDGER,
        }
    )


@pytest.fixture
async def project(db_session: AsyncSession) -> Project:
    client = User(phone=f"+234803{secrets.randbelow(10**7):07d}", role="client", status="active")
    db_session.add(client)
    await db_session.flush()
    data = ProjectCreate(title="Duplex", address="9 Ogui Road, Enugu", currency="NGN", budget_minor=10_000)
    return await projects.create_project(db_session, client, data)


@pytest.fixture
async def agent_user(db_session: AsyncSession) -> User:
    return await seed.upsert_agent_user(db_session, ra.AGENT_NAME)


# Money and citations (pure)


@pytest.mark.parametrize(
    ("minor", "currency", "text"),
    [
        (4_500_000_00, "NGN", "₦4,500,000.00"),
        (5, "NGN", "₦0.05"),
        (-1999, "USD", "-$19.99"),
        (100, "XOF", "1.00 XOF"),
    ],
)
def test_money_is_formatted_from_integer_minor_units(minor: int, currency: str, text: str) -> None:
    assert ra.format_minor(minor, currency) == text


def test_money_section_comes_from_ledger_rows_with_totals() -> None:
    section = ra.money_section(LEDGER["items"][:2])

    assert "₦4,500,000.00" in section and "₦1,250,000.50" in section
    assert "Total credit: ₦4,500,000.00" in section and "Total debit: ₦1,250,000.50" in section


def test_money_section_says_so_when_the_ledger_is_missing_or_quiet() -> None:
    assert "isn't available" in ra.money_section(None)
    assert "No money moved" in ra.money_section([])


@pytest.mark.parametrize(
    "sentence",
    [
        "We spent ₦450,000 on blocks.",
        "About NGN 2m was released.",
        "Roughly 300000 naira remain.",
        "The plumber charged N45,000.",
        "A total of 1,250,000 was paid.",
        "Each bag cost $9.",
        "Only 50 kobo left.",
    ],
)
def test_any_money_in_the_narrative_is_refused(sentence: str) -> None:
    assert ra.check_narrative(f"## This week\n\n{sentence}", []) is None


def test_citations_keep_only_real_evidence_and_are_numbered() -> None:
    text = f"Walls are up [evidence:{PHOTO_B}]. Roof next [evidence:{MADE_UP}]. Again [evidence:{PHOTO_B}]."

    checked = ra.check_narrative(text, [PHOTO_A, PHOTO_B])

    assert checked is not None
    narrative, cited = checked
    assert cited == [PHOTO_B]
    assert narrative == "## This week\n\nWalls are up [photo 1]. Roof next . Again [photo 1]."


def test_plain_numbers_that_are_not_money_are_fine() -> None:
    assert (
        ra.check_narrative("## This week\n\nThe 3 bedrooms reached lintel level on day 12.", []) is not None
    )


# Reading the week's data through the API


async def test_gather_reads_each_route_and_keeps_only_this_weeks_ledger() -> None:
    project_id = uuid.uuid4()
    api = full_api(project_id)

    data = await ra.gather(api, project_id, MONDAY)

    assert [c[1].rsplit("/", 1)[-1] for c in api.calls] == [
        str(project_id),
        "milestones",
        "evidence",
        "ledger",
    ]
    assert api.calls[2][2] == {"since": "2026-10-12"}
    assert data.evidence_ids == [PHOTO_A, PHOTO_B]
    assert data.ledger is not None and [e["amount_minor"] for e in data.ledger] == [
        4_500_000_00,
        1_250_000_50,
    ]


async def test_routes_not_on_main_yet_are_none() -> None:
    project_id = uuid.uuid4()

    data = await ra.gather(FakeApi({"project": {"id": str(project_id)}}), project_id, MONDAY)

    assert (data.milestones, data.evidence, data.ledger) == (None, None, None)


# Whole report


async def test_report_has_model_narrative_and_ledger_money(
    db_session: AsyncSession, project: Project, agent_user: User
) -> None:
    client, models = model(f"## This week\n\nBlockwork reached lintel level [evidence:{PHOTO_A}].")

    outcome = await ra.generate_weekly_report(
        db_session, project.id, MONDAY, caller=full_api(project.id), client=client
    )

    body = outcome.report.body_md
    assert outcome.used_model
    assert "lintel level [photo 1]" in body
    assert "₦4,500,000.00" in body and "₦0.99" not in body  # money from this week's ledger only
    assert body.index("| 1 | Foundation") < body.index("| 2 | Lintel")
    assert outcome.report.evidence_ids == [uuid.UUID(PHOTO_A)]
    prompt = models.requests[0]["contents"][0].parts[-1].text
    assert "4500000" not in prompt and "ledger" not in prompt.split("Data:")[1]  # the model never sees money
    run = await db_session.get(AgentRun, outcome.run_id)
    assert run is not None and run.user_id == agent_user.id


async def test_model_writing_money_falls_back_to_the_plain_summary(
    db_session: AsyncSession, project: Project, agent_user: User
) -> None:
    client, _ = model("## This week\n\nWe paid the roofer ₦300,000.")

    outcome = await ra.generate_weekly_report(
        db_session, project.id, MONDAY, caller=full_api(project.id), client=client
    )

    assert not outcome.used_model
    assert "₦300,000" not in outcome.report.body_md
    assert "produced from the project's data" in outcome.report.body_md
    assert "₦4,500,000.00" in outcome.report.body_md  # the ledger money is still there


async def test_failed_model_run_falls_back_too(
    db_session: AsyncSession, project: Project, agent_user: User
) -> None:
    outcome = await ra.generate_weekly_report(
        db_session,
        project.id,
        MONDAY,
        caller=full_api(project.id),
        client=LLMClient(LLMSettings(llm_api_key="")),
    )

    assert not outcome.used_model and outcome.report.status == "draft"


async def test_missing_agent_user_is_503(
    db_session: AsyncSession, project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agents, "agent_user_id", lambda name: uuid.uuid4())  # an id nobody seeded
    client, models = model("never used")

    with pytest.raises(AppError) as error:
        await ra.generate_weekly_report(
            db_session, project.id, MONDAY, caller=full_api(project.id), client=client
        )

    assert (error.value.code, error.value.status_code) == ("agent_user_missing", 503)
    assert models.requests == []  # refused before the model was asked anything


def test_agent_token_holds_only_read_routes() -> None:
    claims = agents.decode_service_token(
        agents.create_service_token(ra.AGENT_NAME, ra.ROUTES, user_id=agents.agent_user_id(ra.AGENT_NAME))
    )

    assert claims["allowed"] and all(route.startswith("GET /api/v1/projects/") for route in claims["allowed"])


async def test_reads_go_through_the_real_api_with_the_agents_token(
    client: AsyncClient, db_session: AsyncSession, project: Project, agent_user: User
) -> None:
    llm_client, models = model("## This week\n\nWork continued on site.")

    outcome = await ra.generate_weekly_report(db_session, project.id, MONDAY, client=llm_client)

    # The project route exists on main and the agent's token reaches it; the others aren't merged yet.
    prompt = models.requests[0]["contents"][0].parts[-1].text
    assert str(project.id) in prompt and '"title": "Duplex"' in prompt and '"status": "draft"' in prompt
    assert outcome.used_model
    assert "Milestone details aren't available" in outcome.report.body_md
    assert "escrow ledger isn't available" in outcome.report.body_md
