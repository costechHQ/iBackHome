"""iBackHome's funding fee, in basis points, integer maths only. Owner: Gabriel.

    fee_minor(75_000, 250)   # 2.5% of £750.00 -> 1_875 (£18.75)

The fee is charged on top of the converted milestone amount and is ROUNDED UP to a whole minor
unit: ceil(net_minor x bps / 10_000), computed with integers so no float ever touches it.
The rate comes from FUNDING_FEE_BPS (settings) and is stored with each funding (Stripe metadata
and the audit entry), so a later change never rewrites history.
"""

from app.base.payments.settings import get_payments_settings
from app.core.errors import AppError

BPS_DENOMINATOR = 10_000


def fee_minor(net_minor: int, bps: int) -> int:
    if type(net_minor) is not int or net_minor <= 0:
        raise AppError("fee_invalid_amount", f"amount must be a positive integer, got {net_minor!r}.", 422)
    if type(bps) is not int or not 0 <= bps <= BPS_DENOMINATOR:
        raise AppError("fee_invalid_bps", f"fee must be 0..{BPS_DENOMINATOR} basis points, got {bps!r}.", 422)
    return -(-net_minor * bps // BPS_DENOMINATOR)  # ceiling division on integers


def funding_fee_bps() -> int:
    return get_payments_settings().funding_fee_bps
