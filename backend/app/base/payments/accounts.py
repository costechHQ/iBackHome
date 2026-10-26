"""Ledger account names. Build them with these helpers; never hand-type them. Owner: Gabriel.

Every account name ends in its ISO 4217 currency, so one account only ever holds one currency
and `balance()` never adds naira to pounds:

    accounts.client_funding(project_id, "GBP")  -> "client_funding:<project_id>:GBP"
    accounts.escrow(project_id, "NGN")          -> "escrow:<project_id>:NGN"
    accounts.fees("GBP")                        -> "fees:GBP"
"""

import re
import uuid

_CURRENCY = re.compile(r"^[A-Z]{3}$")


def _cur(currency: str) -> str:
    if not _CURRENCY.match(currency):
        raise ValueError(f"currency must be a 3-letter ISO 4217 code in capitals, got {currency!r}")
    return currency


def stripe_clearing(currency: str) -> str:
    """Money Stripe has received for us but not yet passed to the escrow partner."""
    return f"stripe_clearing:{_cur(currency)}"


def client_funding(project_id: uuid.UUID, currency: str) -> str:
    """What a client has paid towards a project, in the client's currency."""
    return f"client_funding:{project_id}:{_cur(currency)}"


def escrow(project_id: uuid.UUID, currency: str) -> str:
    """What the escrow partner holds for a project."""
    return f"escrow:{project_id}:{_cur(currency)}"


def fx_conversion(currency: str) -> str:
    """One leg of a currency conversion (a GBP transaction and an NGN transaction, linked by ref)."""
    return f"fx_conversion:{_cur(currency)}"


def contractor_payable(currency: str) -> str:
    """Released to contractors, not yet confirmed paid out."""
    return f"contractor_payable:{_cur(currency)}"


def supplier_payable(currency: str) -> str:
    """Released to suppliers, not yet confirmed paid out."""
    return f"supplier_payable:{_cur(currency)}"


def escrow_payouts(currency: str) -> str:
    """Payouts the escrow partner (or Paystack) has confirmed."""
    return f"escrow_payouts:{_cur(currency)}"


def fees(currency: str) -> str:
    """iBackHome's own fee income."""
    return f"fees:{_cur(currency)}"


def subscription_revenue(currency: str) -> str:
    """iBackHome's own supervision-subscription income (never escrow money)."""
    return f"subscription_revenue:{_cur(currency)}"


def project_prefixes(project_id: uuid.UUID) -> list[str]:
    """Prefixes of every account that belongs to one project (any currency), for ledger listings."""
    return [f"client_funding:{project_id}:", f"escrow:{project_id}:"]
