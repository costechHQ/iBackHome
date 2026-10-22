"""Paystack API client (NGN payouts), behind one small interface. Owner: Gabriel.

Only the calls payouts need: create a transfer recipient, start a transfer, and look a transfer up
by our reference (to learn what happened when Paystack's answer to a transfer was lost). For people
saving their own payout account there is a second, smaller interface (PaystackDirectory): the list of
Nigerian banks and the account-name lookup. Uses httpx
with the secret key from PAYSTACK_SECRET_KEY (sk_test_... in test mode). Tests mock the HTTP
layer with respx, so they never reach Paystack.

    client = get_paystack_client()
    recipient = await client.create_transfer_recipient("Chidi Okeke", "0123456789", "058")
    transfer = await client.initiate_transfer(5_000_000, recipient.recipient_code, "rel-...", "Milestone 1")

Paystack's own docs: https://paystack.com/docs/transfers/ . Transfers are idempotent on OUR
`reference`: Paystack refuses a second transfer with a reference it has already seen.
"""

from dataclasses import dataclass
from typing import Any, Literal, Protocol

import httpx

from app.base.payments.settings import get_payments_settings
from app.core.errors import AppError

TIMEOUT_SECONDS = 15.0

TransferStatus = Literal["pending", "success", "failed"]


@dataclass(frozen=True)
class RecipientResult:
    recipient_code: str  # RCP_...
    bank_code: str
    bank_name: str
    account_name: str
    account_last4: str  # the only part of the account number we keep


@dataclass(frozen=True)
class TransferResult:
    reference: str
    transfer_code: str  # TRF_...
    status: TransferStatus  # "pending" until the transfer.* webhook says otherwise


@dataclass(frozen=True)
class Bank:
    code: str
    name: str


class PaystackClient(Protocol):
    async def create_transfer_recipient(
        self, account_name: str, account_number: str, bank_code: str
    ) -> RecipientResult: ...

    async def initiate_transfer(
        self, amount_minor: int, recipient_code: str, reference: str, reason: str
    ) -> TransferResult: ...

    async def verify_transfer(self, reference: str) -> TransferResult | None: ...


class PaystackDirectory(Protocol):
    """What someone saving their payout account needs: the banks, and whose name an account is in."""

    async def list_banks(self) -> list[Bank]: ...

    async def resolve_account(self, account_number: str, bank_code: str) -> str: ...


def _transfer_status(raw: object) -> TransferStatus:
    # Paystack also answers "otp" (OTP confirmation is switched on in the dashboard; switch it off
    # for API transfers) and "received"/"processing"; all of them mean "not final yet".
    if raw == "success":
        return "success"
    if raw in ("failed", "abandoned", "rejected"):
        return "failed"
    return "pending"


class HttpPaystackClient:
    def __init__(self, secret_key: str, base_url: str) -> None:
        self._secret_key = secret_key
        self._base_url = base_url.rstrip("/")

    async def _send(self, method: str, path: str, payload: dict[str, Any] | None = None) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=TIMEOUT_SECONDS,
                headers={"Authorization": f"Bearer {self._secret_key}"},
            ) as http:
                return await http.request(method, path, json=payload)
        except httpx.HTTPError as exc:
            raise AppError("paystack_unavailable", "Paystack could not be reached. Try again.", 502) from exc

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._data(await self._send("POST", path, payload))

    @staticmethod
    def _data(response: httpx.Response) -> dict[str, Any]:
        if response.status_code >= 500:
            raise AppError(
                "paystack_unavailable", f"Paystack answered {response.status_code}. Try again.", 502
            )
        try:
            body: dict[str, Any] = response.json()
        except ValueError as exc:
            raise AppError("paystack_unavailable", "Paystack sent an unreadable answer.", 502) from exc
        if response.status_code >= 400 or not body.get("status"):
            # Paystack's message is safe to show (e.g. "Account number is invalid").
            raise AppError(
                "paystack_refused", str(body.get("message") or "Paystack refused the request."), 422
            )
        data = body.get("data")
        if not isinstance(data, dict):
            raise AppError("paystack_unavailable", "Paystack sent no data.", 502)
        return data

    async def create_transfer_recipient(
        self, account_name: str, account_number: str, bank_code: str
    ) -> RecipientResult:
        data = await self._post(
            "/transferrecipient",
            {
                "type": "nuban",
                "name": account_name,
                "account_number": account_number,
                "bank_code": bank_code,
                "currency": "NGN",
            },
        )
        details = data.get("details") or {}
        return RecipientResult(
            recipient_code=str(data["recipient_code"]),
            bank_code=str(details.get("bank_code") or bank_code),
            bank_name=str(details.get("bank_name") or ""),
            account_name=str(details.get("account_name") or data.get("name") or account_name),
            account_last4=str(details.get("account_number") or account_number)[-4:],
        )

    async def initiate_transfer(
        self, amount_minor: int, recipient_code: str, reference: str, reason: str
    ) -> TransferResult:
        data = await self._post(
            "/transfer",
            {
                "source": "balance",
                "amount": amount_minor,
                "currency": "NGN",
                "recipient": recipient_code,
                "reference": reference,
                "reason": reason,
            },
        )
        return TransferResult(
            reference=str(data.get("reference") or reference),
            transfer_code=str(data.get("transfer_code") or ""),
            status=_transfer_status(data.get("status")),
        )

    async def verify_transfer(self, reference: str) -> TransferResult | None:
        """The transfer Paystack has under our reference, or None if it never received one."""
        response = await self._send("GET", f"/transfer/verify/{reference}")
        if response.status_code == 404:
            return None
        data = self._data(response)
        return TransferResult(
            reference=str(data.get("reference") or reference),
            transfer_code=str(data.get("transfer_code") or ""),
            status=_transfer_status(data.get("status")),
        )

    async def list_banks(self) -> list[Bank]:
        """Nigerian banks that take NGN transfers (Paystack GET /bank)."""
        response = await self._send("GET", "/bank?country=nigeria&currency=NGN&perPage=100")
        if response.status_code >= 400:
            self._data(response)  # raises the matching AppError
        try:
            body = response.json()
        except ValueError as exc:
            raise AppError("paystack_unavailable", "Paystack sent an unreadable answer.", 502) from exc
        rows = body.get("data") if isinstance(body, dict) else None
        if not isinstance(rows, list):
            raise AppError("paystack_unavailable", "Paystack sent no banks.", 502)
        banks = {
            str(row["code"]): Bank(code=str(row["code"]), name=str(row["name"]))
            for row in rows
            if isinstance(row, dict) and row.get("code") and row.get("name") and row.get("active", True)
        }
        return sorted(banks.values(), key=lambda b: b.name.lower())

    async def resolve_account(self, account_number: str, bank_code: str) -> str:
        """The name the bank has on the account (Paystack GET /bank/resolve)."""
        response = await self._send(
            "GET", f"/bank/resolve?account_number={account_number}&bank_code={bank_code}"
        )
        data = self._data(response)
        name = str(data.get("account_name") or "").strip()
        if not name:
            raise AppError("paystack_refused", "The bank didn't give a name for this account.", 422)
        return name


def get_paystack_client() -> PaystackClient:
    settings = get_payments_settings()
    if not settings.paystack_secret_key:
        raise AppError("paystack_not_configured", "PAYSTACK_SECRET_KEY is not set.", 503)
    return HttpPaystackClient(settings.paystack_secret_key, settings.paystack_base_url)


def get_paystack_directory() -> PaystackDirectory:
    settings = get_payments_settings()
    if not settings.paystack_secret_key:
        raise AppError("paystack_not_configured", "PAYSTACK_SECRET_KEY is not set.", 503)
    return HttpPaystackClient(settings.paystack_secret_key, settings.paystack_base_url)
