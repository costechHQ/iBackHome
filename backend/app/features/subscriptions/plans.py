"""The three supervision plans (Basic, Standard, Premium). Owner: Christopher.

A plan fixes the monthly price (USD) and how many site visits a month the supervisor makes. Visits are
shown to the client; nothing counts or caps them yet. Prices come from settings.py so they can change
without a code change. Standard is the one we recommend.
"""

from dataclasses import dataclass
from typing import Literal, get_args

from app.features.subscriptions.settings import get_subscription_settings

PlanCode = Literal["basic", "standard", "premium"]
PLAN_CODES: tuple[str, ...] = get_args(PlanCode)
DEFAULT_PLAN: PlanCode = "basic"
RECOMMENDED_PLAN: PlanCode = "premium"
CURRENCY = "USD"


@dataclass(frozen=True)
class Plan:
    code: PlanCode
    name: str
    visits_per_month: int
    amount_minor: int
    currency: str = CURRENCY
    recommended: bool = False


_VISITS: dict[str, tuple[str, int]] = {
    "basic": ("Basic", 2),
    "standard": ("Standard", 3),
    "premium": ("Premium", 4),
}


def get_plan(code: str) -> Plan:
    """One plan with its current price. KeyError for an unknown code (the API validates it first)."""
    name, visits = _VISITS[code]
    return Plan(
        code=code,  # type: ignore[arg-type]
        name=name,
        visits_per_month=visits,
        amount_minor=get_subscription_settings().plan_price_minor(code),
        recommended=code == RECOMMENDED_PLAN,
    )


def list_plans() -> list[Plan]:
    return [get_plan(code) for code in PLAN_CODES]


def visits_for(code: str) -> int:
    return _VISITS[code][1]
