"""HTTP endpoints for the price index. 

Add the signed-in-user check (`current_user`) once Christopher's login lands on backend day 2.
"""

from fastapi import APIRouter

from app.core.db import SessionDep
from app.features.price_index import service
from app.features.price_index.schemas import CurrentPrice

router = APIRouter(tags=["price index"])


@router.get("/price-index", response_model=list[CurrentPrice])
async def get_price_index(session: SessionDep) -> list[CurrentPrice]:
    prices = await service.current_prices(session)
    return sorted(prices.values(), key=lambda p: p.item.lower())
