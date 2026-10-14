"""Render a weekly report's Markdown as a PDF. Owner: James.

The Markdown comes from an LLM, so it is treated as untrusted:
- raw HTML in it is shown as text, never rendered (no injected tags or styles);
- WeasyPrint may not fetch anything (no remote images or stylesheets), so a link in a report
  can never make the server call another machine.

WeasyPrint needs Pango from the operating system. Docker and CI install it; on Windows it is usually
missing, so it is imported only when a PDF is rendered (see `pdf_available()`).
"""

import html
import uuid
from collections.abc import Sequence
from datetime import date, timedelta
from typing import Any, NoReturn

import markdown

_STYLE = """
@page { size: A4; margin: 18mm 16mm 20mm; @bottom-center { content: counter(page) " / " counter(pages);
        font-size: 8pt; color: #777; } }
body { font-family: "DejaVu Sans", Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1d1d1b; }
header { border-bottom: 2px solid #1f6f50; padding-bottom: 6pt; margin-bottom: 12pt; }
header .brand { color: #1f6f50; font-weight: bold; font-size: 9pt; letter-spacing: 0.08em; }
header h1 { font-size: 16pt; margin: 4pt 0 2pt; }
header .week { color: #555; font-size: 9.5pt; }
h2 { font-size: 12.5pt; color: #1f6f50; margin-top: 14pt; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; }
th, td { border: 1px solid #ccc; padding: 3pt 5pt; text-align: left; font-size: 9.5pt; }
th { background: #eef5f1; }
footer { margin-top: 18pt; border-top: 1px solid #ccc; padding-top: 6pt; font-size: 8pt; color: #555; }
footer code { font-size: 7.5pt; }
"""


def _no_fetching(url: str, *args: Any, **kwargs: Any) -> NoReturn:
    raise ValueError(f"reports may not load external resources ({url[:60]})")


def markdown_to_html(body_md: str) -> str:
    """Markdown to HTML with any raw HTML neutralised (shown as text)."""
    # Escaping "&" and "<" before Markdown runs stops every tag; Markdown syntax (#, *, >, |) still works.
    neutralised = body_md.replace("&", "&amp;").replace("<", "&lt;")
    rendered: str = markdown.markdown(neutralised, extensions=["tables", "sane_lists"], output_format="html")
    return rendered


def report_html(body_md: str, *, title: str, week_start: date, evidence_ids: Sequence[uuid.UUID]) -> str:
    week_end = week_start + timedelta(days=6)
    week = f"Week of {week_start:%d %b %Y} – {week_end:%d %b %Y}"
    cited = ", ".join(f"<code>{e}</code>" for e in evidence_ids) or "none"
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{_STYLE}</style></head><body>"
        "<header><div class='brand'>iBACKHOME · WEEKLY REPORT</div>"
        f"<h1>{html.escape(title)}</h1><div class='week'>{week}</div></header>"
        f"<main>{markdown_to_html(body_md)}</main>"
        f"<footer>Evidence cited: {cited}<br>"
        "Money figures come from the escrow ledger. Photos are verified on site by your supervisor.</footer>"
        "</body></html>"
    )


def pdf_available() -> bool:
    """True if WeasyPrint's system libraries are installed (Docker, CI)."""
    try:
        import weasyprint  # noqa: F401
    except OSError:
        return False
    return True


def _refusing_fetcher() -> Any:
    """A WeasyPrint fetcher that loads nothing. A refused image is left out; the PDF still renders."""
    from weasyprint.urls import URLFetcher

    class RefuseAll(URLFetcher):  # type: ignore[misc]  # WeasyPrint ships no type hints
        def fetch(self, url: str, *args: Any, **kwargs: Any) -> NoReturn:
            _no_fetching(url)

    return RefuseAll()


def render_pdf(body_md: str, *, title: str, week_start: date, evidence_ids: Sequence[uuid.UUID]) -> bytes:
    """The report as PDF bytes. Raises OSError where WeasyPrint's system libraries are missing."""
    import weasyprint

    document = weasyprint.HTML(
        string=report_html(body_md, title=title, week_start=week_start, evidence_ids=evidence_ids),
        url_fetcher=_refusing_fetcher(),
    )
    pdf: bytes = document.write_pdf()
    return pdf
