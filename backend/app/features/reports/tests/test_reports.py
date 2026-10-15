"""Reports: drafts (needs Postgres) and HTML/PDF rendering."""

import os
import secrets
import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users.models import User
from app.core.errors import AppError
from app.features.projects import service as projects
from app.features.projects.models import Project
from app.features.projects.schemas import ProjectCreate
from app.features.reports import pdf, service
from app.features.reports.models import ReportStatus

MONDAY = date(2026, 10, 12)
BODY = (
    "## Progress\n\nBlockwork reached **lintel level**.\n\n"
    "| Item | Status |\n| --- | --- |\n| Walls | Done |\n"
)


async def make_user(session: AsyncSession, role: str) -> User:
    user = User(phone=f"+234803{secrets.randbelow(10**7):07d}", role=role, status="active")
    session.add(user)
    await session.flush()
    return user


@pytest.fixture
async def client_user(db_session: AsyncSession) -> User:
    return await make_user(db_session, "client")


@pytest.fixture
async def project(db_session: AsyncSession, client_user: User) -> Project:
    data = ProjectCreate(
        title="Duplex <Ngwo>", address="1 Ngwo Road, Enugu", currency="NGN", budget_minor=10_000
    )
    return await projects.create_project(db_session, client_user, data)


# Pure rendering (no database, no WeasyPrint)


def test_week_start_is_the_monday() -> None:
    assert service.week_start_of(date(2026, 10, 15)) == MONDAY  # a Thursday
    assert service.week_start_of(MONDAY) == MONDAY


def test_markdown_renders_headings_bold_and_tables() -> None:
    html = pdf.markdown_to_html(BODY)

    assert "<h2>Progress</h2>" in html
    assert "<strong>lintel level</strong>" in html
    assert "<table>" in html and "<td>Walls</td>" in html


@pytest.mark.parametrize(
    "attack",
    [
        "<script>alert(1)</script>",
        '<img src="http://169.254.169.254/latest/meta-data">',
        "<style>body{display:none}</style>",
        '<a href="javascript:alert(1)">x</a>',
    ],
)
def test_raw_html_from_the_model_is_shown_as_text(attack: str) -> None:
    html = pdf.markdown_to_html(f"Hello\n\n{attack}")

    assert "<script" not in html and "<img" not in html and "<style" not in html and "<a " not in html
    assert "&lt;" in html


def test_page_escapes_the_title_and_cites_evidence() -> None:
    evidence = [uuid.uuid4(), uuid.uuid4()]

    page = pdf.report_html(BODY, title="Duplex <Ngwo>", week_start=MONDAY, evidence_ids=evidence)

    assert "Duplex &lt;Ngwo&gt;" in page
    assert "Week of 12 Oct 2026 – 18 Oct 2026" in page
    assert all(str(e) in page for e in evidence)


def test_renderer_refuses_to_fetch_anything() -> None:
    with pytest.raises(ValueError):
        pdf._no_fetching("http://169.254.169.254/")


# The real PDF needs Pango: skipped on a laptop without it, required in CI (like the database).


@pytest.fixture
def weasyprint_ready() -> None:
    if not pdf.pdf_available():
        if os.environ.get("CI"):
            pytest.fail("WeasyPrint's system libraries are required in CI")
        pytest.skip("WeasyPrint's system libraries (Pango) aren't installed here; run in Docker")


def test_render_pdf_makes_a_pdf(weasyprint_ready: None) -> None:
    data = pdf.render_pdf(BODY, title="Duplex", week_start=MONDAY, evidence_ids=[uuid.uuid4()])

    assert data.startswith(b"%PDF-")
    assert len(data) > 1000


def test_markdown_image_pointing_elsewhere_is_not_fetched(
    weasyprint_ready: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    refused: list[str] = []
    real_refusal = pdf._no_fetching

    def recording_refusal(url: str, *args: object, **kwargs: object) -> None:
        refused.append(url)
        real_refusal(url)

    monkeypatch.setattr(pdf, "_no_fetching", recording_refusal)

    data = pdf.render_pdf(
        "![x](http://169.254.169.254/secret.png)", title="Duplex", week_start=MONDAY, evidence_ids=[]
    )

    assert data.startswith(b"%PDF-")  # the PDF still renders, just without the image
    assert refused == [
        "http://169.254.169.254/secret.png"
    ]  # the request reached our refusal, not the network


# Drafts (database)


async def test_create_draft_and_list_it(
    db_session: AsyncSession, project: Project, client_user: User
) -> None:
    evidence = [uuid.uuid4(), uuid.uuid4()]

    report = await service.create_draft(db_session, project.id, MONDAY, BODY, [*evidence, evidence[0]])

    assert report.status == ReportStatus.DRAFT.value
    assert report.evidence_ids == evidence  # repeats dropped, order kept
    assert await service.list_for_project(db_session, client_user, project.id) == [report]


async def test_redrafting_the_same_week_replaces_the_draft(
    db_session: AsyncSession, project: Project
) -> None:
    first = await service.create_draft(db_session, project.id, MONDAY, "First version.")
    first.pdf_key = "reports/old.pdf"

    second = await service.create_draft(db_session, project.id, MONDAY, "Second version.")

    assert second.id == first.id
    assert (second.body_md, second.pdf_key) == ("Second version.", None)


async def test_reviewed_report_is_locked(db_session: AsyncSession, project: Project) -> None:
    report = await service.create_draft(db_session, project.id, MONDAY, BODY)
    report.status = ReportStatus.REVIEWED.value
    await db_session.flush()

    with pytest.raises(AppError) as error:
        await service.create_draft(db_session, project.id, MONDAY, "Sneaky rewrite.")

    assert (error.value.code, error.value.status_code) == ("report_locked", 409)


@pytest.mark.parametrize(
    ("week", "body", "code"),
    [
        (date(2026, 10, 14), BODY, "week_not_monday"),
        (MONDAY, "   ", "report_empty"),
        (MONDAY, "x" * (service.MAX_BODY_CHARS + 1), "report_too_long"),
    ],
)
async def test_invalid_drafts_are_refused(
    db_session: AsyncSession, project: Project, week: date, body: str, code: str
) -> None:
    with pytest.raises(AppError) as error:
        await service.create_draft(db_session, project.id, week, body)

    assert (error.value.code, error.value.status_code) == (code, 422)


async def test_draft_for_unknown_project_is_404(db_session: AsyncSession) -> None:
    with pytest.raises(AppError) as error:
        await service.create_draft(db_session, uuid.uuid4(), MONDAY, BODY)

    assert error.value.status_code == 404


async def test_outsider_cannot_list_a_projects_reports(db_session: AsyncSession, project: Project) -> None:
    outsider = await make_user(db_session, "client")

    with pytest.raises(AppError) as error:
        await service.list_for_project(db_session, outsider, project.id)

    assert (error.value.code, error.value.status_code) == ("not_project_member", 403)


async def test_drafting_is_audited(db_session: AsyncSession, project: Project) -> None:
    from app.base.audit.service import search

    report = await service.create_draft(db_session, project.id, MONDAY, BODY)

    entries, _ = await search(db_session, object_id=report.id)
    assert [e.action for e in entries] == ["report.drafted"]
