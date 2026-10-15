"""FX conversion and fees: integer results, one rounding rule (up), rates as Decimal."""

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.base.payments.fees import fee_minor
from app.base.payments.fx import StaticFxRates, foreign_minor_for_ngn
from app.base.payments.settings import get_payments_settings
from app.core.errors import AppError


@pytest.fixture
def rates(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("FX_NGN_PER_GBP", "2050.5")
    monkeypatch.setenv("FX_RATES_AS_OF", "2026-10-14T09:00:00Z")
    get_payments_settings.cache_clear()
    yield
    get_payments_settings.cache_clear()


def test_worked_example_1_5m_naira_at_2000_is_750_pounds_plus_18_75_fee() -> None:
    net = foreign_minor_for_ngn(150_000_000, Decimal("2000"))
    assert net == 75_000
    assert fee_minor(net, 250) == 1_875
    assert net + fee_minor(net, 250) == 76_875


def test_conversion_rounds_up_so_escrow_is_never_short() -> None:
    # 150,000,000 / 2050.5 = 73,152.889... pence -> 73,153
    net = foreign_minor_for_ngn(150_000_000, Decimal("2050.5"))
    assert net == 73_153
    assert Decimal(net) * Decimal("2050.5") >= 150_000_000
    assert Decimal(net - 1) * Decimal("2050.5") < 150_000_000


def test_exact_conversion_is_not_rounded() -> None:
    assert foreign_minor_for_ngn(200_000, Decimal("2000")) == 100


def test_huge_amount_stays_exact() -> None:
    assert foreign_minor_for_ngn(9_000_000_000_000_000_000, Decimal("1")) == 9_000_000_000_000_000_000


@pytest.mark.parametrize("rate", [1500.0, Decimal("0"), Decimal("-1"), Decimal("NaN")])
def test_float_or_bad_rate_is_refused(rate: object) -> None:
    with pytest.raises(AppError) as error:
        foreign_minor_for_ngn(100, rate)  # type: ignore[arg-type]
    assert error.value.code == "fx_invalid_rate"


@pytest.mark.parametrize("amount", [0, -5, 1.5, True])
def test_bad_amount_is_refused(amount: object) -> None:
    with pytest.raises(AppError):
        foreign_minor_for_ngn(amount, Decimal("2000"))  # type: ignore[arg-type]


def test_fee_rounds_up_and_uses_integers() -> None:
    assert fee_minor(1, 250) == 1  # 0.025 of a penny -> 1 penny
    assert fee_minor(40_000, 250) == 1_000
    assert fee_minor(40_001, 250) == 1_001
    assert fee_minor(75_000, 0) == 0


@pytest.mark.parametrize(("net", "bps"), [(0, 250), (100, -1), (100, 10_001), (100, 2.5)])
def test_bad_fee_inputs_are_refused(net: int, bps: object) -> None:
    with pytest.raises(AppError):
        fee_minor(net, bps)  # type: ignore[arg-type]


async def test_static_rates_come_from_settings_as_decimal(rates: None) -> None:
    quote = await StaticFxRates().ngn_per("GBP")
    assert quote.rate == Decimal("2050.5") and isinstance(quote.rate, Decimal)
    assert quote.as_of == datetime(2026, 10, 14, 9, 0, tzinfo=UTC)
    assert quote.source == "static"


async def test_unsupported_currency_is_refused() -> None:
    with pytest.raises(AppError) as error:
        await StaticFxRates().ngn_per("JPY")
    assert (error.value.status_code, error.value.code) == (422, "currency_not_supported")
