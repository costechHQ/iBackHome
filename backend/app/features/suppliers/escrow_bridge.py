"""What suppliers needs from Gabriel's escrow: paying a supplier once a delivery is confirmed.

`confirm_delivery()` calls this in the same transaction that marks the order `delivered`, so a
delivery is never saved without its payment being started. Gabriel's `escrow.pay_supplier()` creates
the release from the project's escrow to the supplier's Paystack recipient (queued after commit);
the order becomes `paid` when Paystack confirms (`suppliers.mark_paid()`). If escrow refuses (409
`supplier_payout_not_set`, `escrow_hold_missing`, `escrow_insufficient_funds`, ...), the error goes
back to the supervisor and nothing is saved. Tests replace this function.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession


async def pay_supplier(session: AsyncSession, order_id: uuid.UUID) -> None:
    # Imported here: escrow's service imports suppliers' service, which imports this module.
    from app.features.escrow import service as escrow

    await escrow.pay_supplier(session, order_id)
