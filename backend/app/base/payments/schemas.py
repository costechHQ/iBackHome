"""Request and response shapes (Pydantic) for payments. Owner: Gabriel."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WebhookAck(BaseModel):
    received: bool
    duplicate: bool  # true when this event was already stored; nothing was done again


class BankOut(BaseModel):
    code: str
    name: str


class AccountIn(BaseModel):
    """A Nigerian bank account: the full number goes to Paystack and is never stored."""

    model_config = ConfigDict(extra="forbid")

    bank_code: str = Field(min_length=2, max_length=10)
    account_number: str = Field(pattern=r"^[0-9]{10}$", description="10-digit NUBAN")


class AccountNameOut(BaseModel):
    account_name: str = Field(description="The name the bank has on the account")


class PayoutRecipientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bank_code: str
    bank_name: str
    account_name: str
    account_number_masked: str = Field(description="Only the last 4 digits, e.g. ******6789")
    currency: str
    created_at: datetime
