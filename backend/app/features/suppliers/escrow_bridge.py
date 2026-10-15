"""What suppliers needs from Gabriel's escrow: paying a supplier once a delivery is confirmed.

Gabriel's `escrow.pay_supplier(session, order_id)` (his Day 4) is not on main yet, so until it is,
this refuses with 503 `escrow_not_ready`: a delivery can then never be confirmed without the payment
being started, and nothing is saved. When his code is merged, replace the body with a call to it:

    from app.features.escrow import service as escrow
    await escrow.pay_supplier(session, order_id)

Nothing else changes. Tests replace this function.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError


async def pay_supplier(session: AsyncSession, order_id: uuid.UUID) -> None:
    raise AppError("escrow_not_ready", "Supplier payment is not connected yet.", 503)
