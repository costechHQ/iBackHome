"""The report's HTML (what becomes the PDF): the two labels, and the supervisor's note under their name."""

import uuid
from datetime import date
from typing import Any

from app.features.reports.pdf import report_html

MONDAY = date(2026, 10, 12)


def html(**kwargs: Any) -> str:
    return report_html(
        "## This week\n\nWalls are up.",
        title="Duplex",
        week_start=MONDAY,
        evidence_ids=[uuid.uuid4()],
        **kwargs,
    )


def test_an_unreviewed_report_is_labelled_ai_generated_only() -> None:
    page = html()
    assert "AI-generated" in page
    assert "Reviewed by" not in page


def test_a_reviewed_report_names_who_reviewed_it() -> None:
    assert "AI-generated · Reviewed by Chidi Nnaji" in html(reviewed_by="Chidi Nnaji")


def test_the_note_is_shown_under_the_writers_name() -> None:
    page = html(note="Rework started Thursday.", note_by="Chidi Nnaji")
    assert "Note from Chidi Nnaji" in page
    assert "Rework started Thursday." in page


def test_a_note_without_a_known_writer_says_your_supervisor() -> None:
    assert "Note from Your supervisor" in html(note="Hello.", note_by=None)


def test_no_note_means_no_note_block() -> None:
    assert "class='note'" not in html()
    assert "class='note'" not in html(note=None, note_by="Chidi Nnaji")


def test_a_note_keeps_its_line_breaks_and_can_never_inject_html() -> None:
    page = html(note="Line one\nLine <script>alert(1)</script> & two", note_by="<b>Eve</b>")
    assert "Line one<br>Line &lt;script&gt;alert(1)&lt;/script&gt; &amp; two" in page
    assert "<script>" not in page
    assert "<b>Eve</b>" not in page
    assert "&lt;b&gt;Eve&lt;/b&gt;" in page


def test_a_reviewers_name_cannot_inject_html_either() -> None:
    page = html(reviewed_by="<i>x</i>")
    assert "<i>x</i>" not in page
    assert "&lt;i&gt;x&lt;/i&gt;" in page


def test_the_ai_text_is_unchanged_by_a_note() -> None:
    page = html(note="Mine.", note_by="Chidi")
    assert "<h2>This week</h2>" in page
    assert "Walls are up." in page
