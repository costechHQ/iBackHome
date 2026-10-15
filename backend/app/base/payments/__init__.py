"""payments: Double-entry ledger, Stripe and Paystack webhooks, payment_events.

Owner: Gabriel (only Gabriel edits this folder).
Spec: FR-13, FR-14. See docs and the Backend Tasks doc for the day-by-day checklist.

What other features import:

    from app.base.payments import accounts, balance, credit, debit, list_entries, post_transaction
    from app.base.payments import webhooks      # @webhooks.handles("stripe", "<event type>")
    from app.base.payments import register_payout_recipient, initiate_transfer   # Paystack payouts
"""

from app.base.payments import accounts
from app.base.payments.service import (
    Entry,
    EntryPage,
    EventResult,
    apply_transfer_event,
    balance,
    credit,
    debit,
    get_payout_recipient,
    initiate_transfer,
    list_entries,
    mark_processed,
    post_transaction,
    record_event,
    register_payout_recipient,
)

__all__ = [
    "Entry",
    "EntryPage",
    "EventResult",
    "accounts",
    "apply_transfer_event",
    "balance",
    "credit",
    "debit",
    "get_payout_recipient",
    "initiate_transfer",
    "list_entries",
    "mark_processed",
    "post_transaction",
    "record_event",
    "register_payout_recipient",
]
