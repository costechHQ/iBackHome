"""payments: Double-entry ledger, Stripe and Paystack webhooks, payment_events.

Owner: Gabriel (only Gabriel edits this folder).
Spec: FR-13, FR-14. See docs and the Backend Tasks doc for the day-by-day checklist.

What other features import:

    from app.base.payments import accounts, balance, credit, debit, list_entries, post_transaction
    from app.base.payments import webhooks      # @webhooks.handles("stripe", "<event type>")
"""

from app.base.payments import accounts
from app.base.payments.service import (
    Entry,
    EntryPage,
    EventResult,
    balance,
    credit,
    debit,
    list_entries,
    mark_processed,
    post_transaction,
    record_event,
)

__all__ = [
    "Entry",
    "EntryPage",
    "EventResult",
    "accounts",
    "balance",
    "credit",
    "debit",
    "list_entries",
    "mark_processed",
    "post_transaction",
    "record_event",
]
