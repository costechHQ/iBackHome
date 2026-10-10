"""Price index: parsing, loading, current prices and GET /price-index.

Prices here are made-up round numbers for testing only, not survey data.
"""

from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import AppError
from app.features.price_index import service
from app.features.price_index.schemas import SurveyRow
from app.main import app

TEMPLATE = Path(__file__).parents[1] / "data" / "survey_template.csv"
TODAY = date(2026, 10, 10)


def row(item: str, price_minor: int, supplier: str, observed_on: date = TODAY) -> SurveyRow:
    return SurveyRow(
        item=item, unit="50 kg bag", price_minor=price_minor, supplier=supplier, observed_on=observed_on
    )


# --- parsing --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "kobo"),
    [("8500", 850_000), ("8,500", 850_000), ("₦8,500.50", 850_050), ("NGN 12000", 1_200_000), ("0.01", 1)],
)
def test_naira_to_kobo(text: str, kobo: int) -> None:
    assert service.naira_to_kobo(text) == kobo


@pytest.mark.parametrize("text", ["", "abc", "0", "-100", "10.001"])
def test_naira_to_kobo_rejects_bad_prices(text: str) -> None:
    with pytest.raises(ValueError):
        service.naira_to_kobo(text)


def test_item_key() -> None:
    assert (
        service.item_key("Long-span aluminium roofing sheet 0.45 mm")
        == "long-span-aluminium-roofing-sheet-0-45-mm"
    )


def test_template_has_at_least_15_items_and_parses_as_blank() -> None:
    rows, skipped = service.parse_survey_csv(TEMPLATE.read_text(encoding="utf-8"))
    assert rows == []
    assert skipped >= 15


def test_parse_survey_csv_reads_filled_rows() -> None:
    text = (
        "item,unit,price_naira,supplier,observed_on\n"
        'Cement 42.5R,50 kg bag,"9,000",Supplier A,2026-10-08\n'
        "Iron rod 12 mm,12 m length,,,\n"
    )
    rows, skipped = service.parse_survey_csv(text)
    assert skipped == 1
    assert rows == [
        SurveyRow(
            item="Cement 42.5R",
            unit="50 kg bag",
            price_minor=900_000,
            supplier="Supplier A",
            observed_on=date(2026, 10, 8),
        )
    ]


def test_parse_survey_csv_lists_every_bad_line() -> None:
    text = (
        "item,unit,price_naira,supplier,observed_on\n"
        "Cement 42.5R,50 kg bag,abc,Supplier A,2026-10-08\n"
        "Cement 42.5R,50 kg bag,9000,Supplier B,08/10/2026\n"
    )
    with pytest.raises(AppError) as error:
        service.parse_survey_csv(text)
    assert "line 2" in error.value.message
    assert "line 3" in error.value.message


def test_parse_survey_csv_requires_columns() -> None:
    with pytest.raises(AppError) as error:
        service.parse_survey_csv("item,price\nCement,9000\n")
    assert "unit" in error.value.message


# --- loading and current prices -----------------------------------------------------------


async def test_load_is_safe_to_run_twice(db_session: AsyncSession) -> None:
    await service.load_survey(db_session, [row("Cement 42.5R", 900_000, "A")])
    await service.load_survey(db_session, [row("Cement 42.5R", 950_000, "A")])
    prices = await service.current_prices(db_session, today=TODAY)
    assert prices["cement-42-5r"].supplier_count == 1
    assert prices["cement-42-5r"].price_minor == 950_000


async def test_current_price_is_median_of_each_suppliers_latest(db_session: AsyncSession) -> None:
    await service.load_survey(
        db_session,
        [
            row("Cement 42.5R", 800_000, "A", date(2026, 9, 1)),  # A's old price: ignored
            row("Cement 42.5R", 900_000, "A", date(2026, 10, 8)),
            row("Cement 42.5R", 950_000, "B", date(2026, 10, 7)),
            row("Cement 42.5R", 2_000_000, "C", date(2026, 10, 6)),  # outlier barely moves a median
        ],
    )
    price = (await service.current_prices(db_session, today=TODAY))["cement-42-5r"]
    assert price.price_minor == 950_000
    assert (price.low_minor, price.high_minor) == (900_000, 2_000_000)
    assert price.supplier_count == 3
    assert price.last_observed_on == date(2026, 10, 8)
    assert price.stale is False


async def test_even_number_of_suppliers_uses_middle_average(db_session: AsyncSession) -> None:
    await service.load_survey(db_session, [row("Binding wire", 100, "A"), row("Binding wire", 201, "B")])
    assert (await service.current_prices(db_session, today=TODAY))["binding-wire"].price_minor == 150


async def test_old_prices_are_marked_stale(db_session: AsyncSession) -> None:
    await service.load_survey(db_session, [row("Laterite", 5_000_000, "A", date(2026, 9, 1))])
    assert (await service.current_prices(db_session, today=TODAY))["laterite"].stale is True


# --- GET /price-index ------------------------------------------------------------------------


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_session, None)


async def test_get_price_index(client: AsyncClient, db_session: AsyncSession) -> None:
    await service.load_survey(
        db_session, [row("Sharp sand", 6_000_000, "A"), row("Cement 42.5R", 900_000, "A")]
    )
    response = await client.get("/api/v1/price-index")
    assert response.status_code == 200
    body = response.json()
    assert [p["item"] for p in body] == ["Cement 42.5R", "Sharp sand"]
    assert body[0]["price_minor"] == 900_000
    assert body[0]["currency"] == "NGN"
