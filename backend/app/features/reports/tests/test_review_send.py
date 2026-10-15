"""Reviewing, sending and the weekly jobs (service.py, router.py, tasks.py). Needs Postgres.

PDF rendering and storage are replaced by fakes here; test_reports.py renders real PDFs (in Docker/CI).
"""

import secrets
import uuid
from datetime import UTC, date, datetime
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.service import search
from app.base.users import service as users
from app.base.users.models import User
from app.core.errors import AppError
from app.features.agents import report_agent
from app.features.agents import service as agents
from app.features.projects import service as projects
from app.features.projects.models import Project, ProjectStatus
from app.features.projects.schemas import ProjectCreate
from app.features.projects.transitions import ActorRole
from app.features.reports import pdf, service, storage, tasks
from app.features.reports.models import Report, ReportStatus
from app.features.supervision import service as supervision
from app.features.supervision.tests.factories import application, approval
from app.workers.celery_app import celery_app
from scripts import seed

MONDAY = date(2026, 10, 12)


async def make_user(session: AsyncSession, role: str) -> User:
    user = User(phone=f"+234803{secrets.randbelow(10**7):07d}", role=role, status="active")
    session.add(user)
    await session.flush()
    return user


def bearer(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {users.create_access_token(user)}"}


class Uploads:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def put(self, key: str, data: bytes) -> None:
        self.files[key] = data


@pytest.fixture
def uploads(monkeypatch: pytest.MonkeyPatch) -> Uploads:
    store = Uploads()
    monkeypatch.setattr(pdf, "render_pdf", lambda body, **_: b"%PDF-1.7 " + body.encode()[:20])
    monkeypatch.setattr(storage, "put_pdf", store.put)
    monkeypatch.setattr(storage, "presign_read", lambda key: f"https://files.test/{key}?sig=1")
    return store


@pytest.fixture
async def people(db_session: AsyncSession) -> dict[str, User]:
    roles = ["client", "contractor", "supervisor", "ops"]
    found = {role: await make_user(db_session, role) for role in roles}
    found["other_supervisor"] = await make_user(db_session, "supervisor")
    return found


@pytest.fixture
async def project(db_session: AsyncSession, people: dict[str, User]) -> Project:
    data = ProjectCreate(
        title="Duplex",
        address="9 Ogui Road, Enugu",
        currency="NGN",
        budget_minor=10_000,
        contractor_phone=people["contractor"].phone,
    )
    created = await projects.create_project(db_session, people["client"], data)
    supervisor, ops = people["supervisor"], people["ops"]
    await supervision.submit_application(db_session, supervisor.id, application())
    await supervision.vet(db_session, supervisor.id, approval(), ops.id)
    return await projects.set_supervisor(db_session, created.id, supervisor.id, ops.id)


@pytest.fixture
async def draft(db_session: AsyncSession, project: Project) -> Report:
    return await service.create_draft(db_session, project.id, MONDAY, "## This week\n\nWalls are up.")


# Review


@pytest.mark.parametrize("reviewer", ["supervisor", "ops"])
async def test_supervisor_or_ops_reviews_and_the_pdf_is_stored(
    db_session: AsyncSession, people: dict[str, User], draft: Report, uploads: Uploads, reviewer: str
) -> None:
    reviewed = await service.review(db_session, draft.id, people[reviewer])

    assert reviewed.status == ReportStatus.REVIEWED.value
    assert reviewed.pdf_key == f"reports/{draft.project_id}/2026-10-12.pdf"
    assert uploads.files[reviewed.pdf_key].startswith(b"%PDF-")
    entries, _ = await search(db_session, object_id=draft.id)
    assert [e.action for e in entries][0] == "report.reviewed"


@pytest.mark.parametrize("who", ["client", "contractor", "other_supervisor"])
async def test_others_cannot_review(
    db_session: AsyncSession, people: dict[str, User], draft: Report, uploads: Uploads, who: str
) -> None:
    with pytest.raises(AppError) as error:
        await service.review(db_session, draft.id, people[who])

    assert (error.value.code, error.value.status_code) == ("not_report_reviewer", 403)


async def test_a_report_is_reviewed_only_once(
    db_session: AsyncSession, people: dict[str, User], draft: Report, uploads: Uploads
) -> None:
    await service.review(db_session, draft.id, people["supervisor"])

    with pytest.raises(AppError) as error:
        await service.review(db_session, draft.id, people["ops"])

    assert (error.value.code, error.value.status_code) == ("invalid_transition", 409)


async def test_no_pdf_means_no_review(
    db_session: AsyncSession, people: dict[str, User], draft: Report, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_pango(*_: Any, **__: Any) -> bytes:
        raise OSError("cannot load library 'libpango-1.0-0'")

    monkeypatch.setattr(pdf, "render_pdf", no_pango)

    with pytest.raises(AppError) as error:
        await service.review(db_session, draft.id, people["supervisor"])

    assert (error.value.code, error.value.status_code) == ("pdf_unavailable", 503)
    assert draft.status == ReportStatus.DRAFT.value and draft.pdf_key is None


# Endpoints


async def test_review_endpoint_and_listing_with_pdf_link(
    client: AsyncClient, people: dict[str, User], project: Project, draft: Report, uploads: Uploads
) -> None:
    reviewed = await client.post(
        f"/api/v1/reports/{draft.id}/review",
        headers=bearer(people["supervisor"]) | {"Idempotency-Key": "rv-1"},
    )
    again = await client.post(
        f"/api/v1/reports/{draft.id}/review",
        headers=bearer(people["supervisor"]) | {"Idempotency-Key": "rv-1"},
    )
    listed = await client.get(f"/api/v1/projects/{project.id}/reports", headers=bearer(people["client"]))

    assert reviewed.status_code == 200 and reviewed.json()["status"] == "reviewed"
    assert again.status_code == 200 and again.json() == reviewed.json()  # same key: replayed, not a 409
    assert listed.status_code == 200
    assert listed.json()[0]["pdf_url"].startswith("https://files.test/reports/")


async def test_outsider_gets_403_on_the_list_and_the_review(
    client: AsyncClient, db_session: AsyncSession, project: Project, draft: Report, uploads: Uploads
) -> None:
    outsider = await make_user(db_session, "client")

    listed = await client.get(f"/api/v1/projects/{project.id}/reports", headers=bearer(outsider))
    reviewed = await client.post(f"/api/v1/reports/{draft.id}/review", headers=bearer(outsider))

    assert (listed.status_code, reviewed.status_code) == (403, 403)


async def test_review_of_unknown_report_is_404(client: AsyncClient, people: dict[str, User]) -> None:
    response = await client.post(f"/api/v1/reports/{uuid.uuid4()}/review", headers=bearer(people["ops"]))

    assert response.status_code == 404


# Sending


async def reviewed_report(session: AsyncSession, project: Project, people: dict[str, User]) -> Report:
    report = await service.create_draft(session, project.id, MONDAY, "## This week\n\nRoof is on.")
    return await service.review(session, report.id, people["ops"])


async def test_delivered_reports_become_sent(
    db_session: AsyncSession, project: Project, people: dict[str, User], uploads: Uploads
) -> None:
    report = await reviewed_report(db_session, project, people)
    delivered: list[uuid.UUID] = []

    async def sender(_: AsyncSession, r: Report, p: Project) -> bool:
        delivered.append(r.id)
        return p.client_id == people["client"].id

    assert await service.send_reviewed(db_session, sender) == 1
    assert delivered == [report.id]
    assert report.status == ReportStatus.SENT.value and report.sent_at is not None


async def test_undelivered_or_failing_reports_stay_reviewed(
    db_session: AsyncSession, project: Project, people: dict[str, User], uploads: Uploads
) -> None:
    report = await reviewed_report(db_session, project, people)

    async def broken(*_: Any) -> bool:
        raise ConnectionError("WhatsApp is down")

    async def not_delivered(*_: Any) -> bool:
        return False

    assert await service.send_reviewed(db_session, broken) == 0
    assert await service.send_reviewed(db_session, not_delivered) == 0
    assert report.status == ReportStatus.REVIEWED.value and report.sent_at is None


async def test_until_notify_exists_the_default_sender_never_marks_sent(
    db_session: AsyncSession, project: Project, people: dict[str, User], uploads: Uploads
) -> None:
    report = await reviewed_report(db_session, project, people)

    await service.send_reviewed(db_session)

    assert report.status == ReportStatus.REVIEWED.value


# The Friday job


async def activate(session: AsyncSession, project: Project) -> None:
    await projects.transition(session, project.id, ProjectStatus.BOQ_REVIEW, ActorRole.CONTRACTOR)
    await projects.transition(session, project.id, ProjectStatus.ACTIVE, ActorRole.SYSTEM)


async def test_friday_job_drafts_active_projects_only(
    db_session: AsyncSession, project: Project, people: dict[str, User], monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed.upsert_agent_user(db_session, report_agent.AGENT_NAME)
    await activate(db_session, project)
    idle = await projects.create_project(
        db_session,
        people["client"],
        ProjectCreate(title="Idle", address="1 Road", currency="NGN", budget_minor=1),
    )
    drafted: list[uuid.UUID] = []

    async def fake_generate(session: AsyncSession, project_id: uuid.UUID, week_start: date) -> Any:
        drafted.append(project_id)
        assert week_start == MONDAY
        return type("Outcome", (), {"used_model": True})()

    monkeypatch.setattr(report_agent, "generate_weekly_report", fake_generate)

    counts = await tasks.generate_all(db_session, today=datetime(2026, 10, 16, 15, 0, tzinfo=UTC))

    assert project.id in drafted and idle.id not in drafted
    assert counts["drafted"] >= 1 and counts["failed"] == 0


async def test_friday_job_without_the_agent_user_drafts_nothing(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(agents, "agent_user_id", lambda name: uuid.uuid4())  # an id nobody seeded

    counts = await tasks.generate_all(db_session)

    assert counts == {"drafted": 0, "fallback": 0, "skipped": 0, "failed": 0}


def test_beat_runs_friday_15_utc_and_every_15_minutes() -> None:
    schedule = celery_app.conf.beat_schedule
    weekly, sending = (
        schedule["reports.generate_weekly"]["schedule"],
        schedule["reports.send_reviewed"]["schedule"],
    )

    assert (weekly.day_of_week, weekly.hour, weekly.minute) == ({5}, {15}, {0})
    assert sending.minute == set(range(0, 60, 15))
