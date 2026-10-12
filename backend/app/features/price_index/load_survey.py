"""Load the materials price survey into the price index.

    python -m app.features.price_index.load_survey path/to/survey.csv

Start from data/survey_template.csv: one row per item, per supplier, per day.
Prices are in naira (e.g. 8500 or 8,500.00). Safe to run again after fixing or adding rows.
"""

import asyncio
import sys
from pathlib import Path

from app.core.db import SessionLocal, engine
from app.core.errors import AppError
from app.features.price_index.schemas import SurveyRow
from app.features.price_index.service import current_prices, load_survey, parse_survey_csv


async def save(rows: list[SurveyRow]) -> tuple[int, int]:
    async with SessionLocal() as session:
        saved = await load_survey(session, rows)
        await session.commit()
        prices = await current_prices(session)
    await engine.dispose()
    return saved, len(prices)


def main(path: Path) -> int:
    try:
        rows, skipped = parse_survey_csv(path.read_text(encoding="utf-8"))
    except AppError as exc:
        print(f"Not loaded: {exc.message}", file=sys.stderr)
        return 1

    saved, item_count = asyncio.run(save(rows))
    print(f"Saved {saved} price observations ({skipped} blank template rows skipped).")
    print(f"The index now has {item_count} items.")
    if item_count < 15:
        print("Warning: the spec asks for at least 15 items.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.features.price_index.load_survey <survey.csv>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(Path(sys.argv[1])))
