"""Exchange rates and the one conversion rule. Owner: Gabriel.

Rates are naira per ONE unit of the client's currency (e.g. 2000 = ₦2,000 per £1), held as
Decimal, never float. Code asks an `FxRateSource` for a quote; `StaticFxRates` reads the rates
from settings (test mode, local, staging). A live rate provider gets its own class later and
nothing else changes.

    quote = await get_fx_source().ngn_per("GBP")      # FxQuote(rate=Decimal("2000"), as_of=..., ...)
    pence = foreign_minor_for_ngn(150_000_000, quote.rate)   # ₦1,500,000.00 -> 75_000 (£750.00)

The rounding rule, applied exactly once per conversion: the client-currency amount is
ROUNDED UP to the next whole minor unit. The naira side is fixed (it is the milestone amount the
escrow must hold), so rounding up means the client pays at most one penny/cent more and the
escrow is never short. The rate used is stored with the conversion (Stripe metadata and the
`fx_rate` column on the conversion's ledger entries).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal, localcontext
from functools import lru_cache
from typing import Literal, Protocol, get_args

from app.base.payments.settings import get_payments_settings
from app.core.errors import AppError

FundingCurrency = Literal["GBP", "USD", "EUR"]
FUNDING_CURRENCIES: tuple[str, ...] = get_args(FundingCurrency)

# ISO 4217 minor-unit exponents of the currencies we convert. All are 2 today; the formula
# below still uses them so a 0- or 3-decimal currency could never be converted wrongly.
MINOR_UNIT_EXPONENT = {"NGN": 2, "GBP": 2, "USD": 2, "EUR": 2}


@dataclass(frozen=True)
class FxQuote:
    currency: str  # the client's currency, e.g. "GBP"
    rate: Decimal  # NGN per 1 unit of `currency`
    as_of: datetime  # UTC
    source: str  # where the rate came from, e.g. "static"


class FxRateSource(Protocol):
    async def ngn_per(self, currency: str) -> FxQuote: ...


def _unsupported(currency: str) -> AppError:
    return AppError(
        "currency_not_supported",
        f"Funding currency must be one of {', '.join(FUNDING_CURRENCIES)}, got {currency!r}.",
        422,
    )


class StaticFxRates:
    """Rates from settings (FX_NGN_PER_GBP / _USD / _EUR). For test mode, local and staging."""

    async def ngn_per(self, currency: str) -> FxQuote:
        settings = get_payments_settings()
        rates = {
            "GBP": settings.fx_ngn_per_gbp,
            "USD": settings.fx_ngn_per_usd,
            "EUR": settings.fx_ngn_per_eur,
        }
        rate = rates.get(currency)
        if rate is None:
            raise _unsupported(currency)
        as_of = settings.fx_rates_as_of or datetime.now(UTC)
        return FxQuote(currency=currency, rate=rate, as_of=as_of.astimezone(UTC), source="static")


@lru_cache
def get_fx_source() -> FxRateSource:
    return StaticFxRates()


def foreign_minor_for_ngn(amount_ngn_minor: int, rate: Decimal, currency: str = "GBP") -> int:
    """Client-currency minor units needed to deliver `amount_ngn_minor`, rounded UP (see module doc)."""
    if type(amount_ngn_minor) is not int or amount_ngn_minor <= 0:
        raise AppError(
            "fx_invalid_amount", f"amount must be a positive integer, got {amount_ngn_minor!r}.", 422
        )
    if not isinstance(rate, Decimal) or not rate.is_finite() or rate <= 0:
        raise AppError("fx_invalid_rate", "rate must be a positive Decimal (never a float).", 422)
    if currency not in MINOR_UNIT_EXPONENT:
        raise _unsupported(currency)
    shift = MINOR_UNIT_EXPONENT[currency] - MINOR_UNIT_EXPONENT["NGN"]
    with localcontext() as ctx:
        ctx.prec = 60  # far more digits than any BIGINT amount needs, so the division is exact enough
        foreign = Decimal(amount_ngn_minor).scaleb(shift) / rate
        return int(foreign.to_integral_value(rounding=ROUND_CEILING))
