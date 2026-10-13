"""Price index rules.

Used by:
- Gabriel (quote checker): current_prices()
- Abigail (material orders): current_prices()
- James (survey data):       load_survey() via the CSV loader
"""

import csv
import io
import re
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.price_index.models import PriceIndexEntry
from app.features.price_index.schemas import CurrentPrice, SurveyRow

STALE_AFTER = timedelta(days=14)
CSV_COLUMNS = ("item", "unit", "price_naira", "supplier", "observed_on")


def item_key(item: str) -> str:
    """'Cement (50 kg bag)' -> 'cement-50-kg-bag'. Stable key used to match quote lines."""
    return re.sub(r"[^a-z0-9]+", "-", item.lower()).strip("-")


def naira_to_kobo(text: str) -> int:
    """'₦8,500.50' -> 850050. Exact decimal maths; refuses zero, negatives and fractions of a kobo."""
    cleaned = text.replace("₦", "").replace(",", "").replace("NGN", "").strip()
    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"'{text}' is not a price") from exc
    if value <= 0:
        raise ValueError(f"price must be above zero, got '{text}'")
    kobo = value * 100
    if kobo != kobo.to_integral_value():
        raise ValueError(f"'{text}' has more than 2 decimal places")
    return int(kobo)


def parse_survey_csv(text: str) -> tuple[list[SurveyRow], int]:
    """Read the survey CSV. Returns (rows, skipped_blank_rows).

    Columns: item, unit, price_naira, supplier, observed_on (YYYY-MM-DD), optional source.
    Rows whose price, supplier and date are all blank (unfilled template lines) are skipped.
    Any other problem raises AppError listing every bad line, so the file can be fixed in one go.
    """
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    headers = [h.strip().lower() for h in (reader.fieldnames or [])]
    missing = [c for c in CSV_COLUMNS if c not in headers]
    if missing:
        raise AppError("invalid_survey_file", f"Missing column(s): {', '.join(missing)}", 422)

    rows: list[SurveyRow] = []
    problems: list[str] = []
    skipped = 0
    for line_no, raw in enumerate(reader, start=2):
        record = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        if not any(record.get(c) for c in ("price_naira", "supplier", "observed_on")):
            skipped += 1
            continue
        try:
            rows.append(
                SurveyRow(
                    item=record["item"],
                    unit=record["unit"],
                    price_minor=naira_to_kobo(record["price_naira"]),
                    supplier=record["supplier"],
                    observed_on=date.fromisoformat(record["observed_on"]),
                    source=record.get("source") or "survey",
                )
            )
        except (ValueError, KeyError) as exc:
            problems.append(f"line {line_no}: {exc}".splitlines()[0])
    if problems:
        raise AppError("invalid_survey_file", "; ".join(problems[:20]), 422)
    return rows, skipped


async def load_survey(session: AsyncSession, rows: Iterable[SurveyRow]) -> int:
    """Save survey rows. Re-loading the same item, supplier and day updates the price instead of
    adding a duplicate, so the loader is safe to run twice. Caller commits. Returns rows saved."""
    count = 0
    for row in rows:
        values = {
            "item_key": item_key(row.item),
            "item": row.item,
            "unit": row.unit,
            "price_minor": row.price_minor,
            "currency": "NGN",
            "supplier_name": row.supplier,
            "observed_on": row.observed_on,
            "source": row.source,
        }
        statement = insert(PriceIndexEntry).values(**values)
        statement = statement.on_conflict_do_update(
            constraint="uq_price_index_entries_observation",
            set_={
                "item": statement.excluded.item,
                "unit": statement.excluded.unit,
                "price_minor": statement.excluded.price_minor,
                "source": statement.excluded.source,
                "updated_at": datetime.now(UTC),
            },
        )
        await session.execute(statement)
        count += 1
    return count


def _median(values: list[int]) -> int:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) // 2  # whole kobo, rounded down


async def current_prices(session: AsyncSession, today: date | None = None) -> dict[str, CurrentPrice]:
    """The index price per item: the median of each supplier's most recent price.

    Using each supplier's latest price (not every old row) stops one supplier who was surveyed
    many times from dominating; the median stops one unusual quote from moving the index.
    """
    today = today or datetime.now(UTC).date()
    entries = await session.scalars(
        select(PriceIndexEntry).order_by(
            PriceIndexEntry.item_key, PriceIndexEntry.supplier_name, PriceIndexEntry.observed_on.desc()
        )
    )

    latest_by_supplier: dict[str, dict[str, PriceIndexEntry]] = defaultdict(dict)
    for entry in entries:
        # Rows arrive newest first per supplier, so keep the first one seen.
        latest_by_supplier[entry.item_key].setdefault(entry.supplier_name, entry)

    result: dict[str, CurrentPrice] = {}
    for key, by_supplier in latest_by_supplier.items():
        latest = list(by_supplier.values())
        prices = [e.price_minor for e in latest]
        newest = max(latest, key=lambda e: e.observed_on)
        result[key] = CurrentPrice(
            item_key=key,
            item=newest.item,
            unit=newest.unit,
            currency=newest.currency,
            price_minor=_median(prices),
            low_minor=min(prices),
            high_minor=max(prices),
            supplier_count=len(latest),
            last_observed_on=newest.observed_on,
            stale=today - newest.observed_on > STALE_AFTER,
        )
    return result
