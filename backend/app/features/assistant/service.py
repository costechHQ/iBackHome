"""Answering a visitor's question (ADR 0006). Owner: Christopher.

The answer is always one of the vetted entries in knowledge.py, with its placeholders filled in at request
time: prices and the funding fee come from the plan list and the fee setting (never typed, never
generated), contact details from settings. No model, no database, no personal data, and nothing a
visitor typed is kept.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.base.payments.fees import funding_fee_bps
from app.features.assistant import knowledge, matcher
from app.features.assistant.knowledge import Entry
from app.features.assistant.settings import get_assistant_settings
from app.features.subscriptions import service as subscriptions


@dataclass(frozen=True)
class Answer:
    text: str
    related: list[str]
    handoff: bool
    source: str  # "faq" or "none"
    entry_id: str | None


def _usd(minor: int) -> str:
    """US cents as dollars, e.g. 10000 -> "$100", 12550 -> "$125.50". Integer maths, never floats."""
    dollars, cents = divmod(minor, 100)
    return f"${dollars:,}" if cents == 0 else f"${dollars:,}.{cents:02d}"


def _percent(bps: int) -> str:
    """Basis points as a percentage, e.g. 250 -> "2.5%", 100 -> "1%"."""
    return f"{(Decimal(bps) / 100).normalize():f}%"


def context() -> dict[str, Any]:
    """The values answers may use: contact details, the plan prices and visits, and the funding fee."""
    settings = get_assistant_settings()
    ctx: dict[str, Any] = {
        "contact_email": settings.assistant_contact_email,
        "contact_whatsapp": settings.assistant_contact_whatsapp,
        "funding_fee": _percent(funding_fee_bps()),
    }
    for plan in subscriptions.list_plans():
        ctx[f"plan_{plan.code}_price"] = _usd(plan.amount_minor)
        ctx[f"visits_{plan.code}"] = plan.visits_per_month
    return ctx


def render(text: str, ctx: dict[str, Any] | None = None) -> str:
    """Fill the placeholders. A placeholder with no value is a bug in knowledge.py, so it raises."""
    return text.format_map(ctx if ctx is not None else context())


def answer(message: str) -> Answer:
    """The best vetted answer for this question, or a handoff to a person when nothing matches well enough."""
    ctx = context()
    match, related = matcher.best(message)
    if match is None:
        return Answer(render(knowledge.FALLBACK_ANSWER, ctx), [], True, "none", None)
    entry: Entry = match.entry
    return Answer(
        text=render(entry.answer, ctx),
        related=[r.questions[0] for r in related],
        handoff=entry.handoff,
        source="faq",
        entry_id=entry.id,
    )
