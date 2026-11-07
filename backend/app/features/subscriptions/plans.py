"""The three supervision plans (Basic, Standard, Premium). Owner: Christopher.

A plan fixes the monthly price (USD) and how many site visits a month the supervisor makes. Visits are
shown to the client; nothing counts or caps them yet. Prices come from settings.py so they can change
without a code change. Premium is the one we recommend.

The client also picks a billing period. Paying for 6 months (bi-annual) costs 5 months and paying for 12
months (annual) costs 10 months, so the discount is one and two months free. The period price is always
the monthly price times the months paid; nothing else is stored.
"""

from dataclasses import dataclass
from typing import Literal, get_args

from app.features.subscriptions.settings import get_subscription_settings

PlanCode = Literal["basic", "standard", "premium"]
BillingPeriod = Literal["monthly", "biannual", "annual"]
PLAN_CODES: tuple[str, ...] = get_args(PlanCode)
DEFAULT_PLAN: PlanCode = "basic"
RECOMMENDED_PLAN: PlanCode = "premium"
DEFAULT_PERIOD: BillingPeriod = "monthly"
CURRENCY = "USD"

# months covered by one invoice, and how many of them are paid for
PERIOD_MONTHS: dict[str, tuple[int, int]] = {
    "monthly": (1, 1),
    "biannual": (6, 5),
    "annual": (12, 10),
}
PERIOD_CODES: tuple[str, ...] = get_args(BillingPeriod)


@dataclass(frozen=True)
class PeriodPrice:
    period: BillingPeriod
    months: int  # months covered by one invoice
    paid_months: int  # months actually paid for (the rest are free)
    amount_minor: int  # charged each billing period, in US cents
    list_amount_minor: int  # the same months at the monthly price, before the discount
    monthly_equivalent_minor: int  # amount_minor spread over the months (rounded down)


@dataclass(frozen=True)
class Plan:
    code: PlanCode
    name: str
    visits_per_month: int
    amount_minor: int
    currency: str = CURRENCY
    recommended: bool = False
    periods: tuple[PeriodPrice, ...] = ()


_VISITS: dict[str, tuple[str, int]] = {
    "basic": ("Basic", 2),
    "standard": ("Standard", 3),
    "premium": ("Premium", 4),
}


def _period_price(monthly: int, period: BillingPeriod) -> PeriodPrice:
    months, paid = PERIOD_MONTHS[period]
    amount = monthly * paid
    return PeriodPrice(
        period=period,
        months=months,
        paid_months=paid,
        amount_minor=amount,
        list_amount_minor=monthly * months,
        monthly_equivalent_minor=amount // months,
    )


def period_price(code: str, period: str) -> PeriodPrice:
    """What one invoice costs for this plan and billing period. KeyError for an unknown code or period."""
    monthly = get_subscription_settings().plan_price_minor(code)
    if period not in PERIOD_MONTHS:
        raise KeyError(period)
    return _period_price(monthly, period)  # type: ignore[arg-type]


def get_plan(code: str) -> Plan:
    """One plan with its current price. KeyError for an unknown code (the API validates it first)."""
    name, visits = _VISITS[code]
    monthly = get_subscription_settings().plan_price_minor(code)
    return Plan(
        code=code,  # type: ignore[arg-type]
        name=name,
        visits_per_month=visits,
        amount_minor=monthly,
        recommended=code == RECOMMENDED_PLAN,
        periods=tuple(_period_price(monthly, period) for period in PERIOD_CODES),  # type: ignore[arg-type]
    )


def list_plans() -> list[Plan]:
    return [get_plan(code) for code in PLAN_CODES]


def visits_for(code: str) -> int:
    return _VISITS[code][1]
