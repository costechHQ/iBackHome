"""The escrow partner, behind one interface. Owner: Gabriel.

iBackHome never holds client money: a licensed escrow partner holds it and releases it.
Code in features/escrow talks to the partner only through `EscrowProvider`, obtained from
`get_escrow_provider()`. Nothing outside features/escrow may import a concrete provider.

    provider = get_escrow_provider()
    hold = await provider.hold(project_id, 150_000_000, "NGN", ref=str(payment_event_id))
    rel = await provider.release(hold.provider_ref, "contractor:<user_id>", 50_000_000, ref=str(release_id))

`ref` is our idempotency key: calling again with the same ref returns the first result and
never holds or releases twice. Reusing a ref with different arguments is refused (409).
"""

import hashlib
import re
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, Protocol

from app.core.errors import AppError
from app.features.escrow.settings import get_escrow_settings

HoldStatus = Literal["held", "pending", "failed"]
ReleaseStatus = Literal["released", "submitted", "failed"]
Operation = Literal["hold", "release", "balance"]

_CURRENCY = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class HoldResult:
    provider_ref: str  # the partner's id for this hold; pass it to release()
    status: HoldStatus  # "pending" means the partner will confirm by webhook
    project_id: uuid.UUID
    amount_minor: int
    currency: str
    ref: str


@dataclass(frozen=True)
class ReleaseResult:
    provider_ref: str
    status: ReleaseStatus  # "submitted" means the partner will confirm by webhook
    hold_ref: str
    payee: str
    amount_minor: int
    currency: str
    ref: str


@dataclass(frozen=True)
class Balance:
    project_id: uuid.UUID
    currency: str | None  # None when nothing has ever been held for the project
    held_minor: int  # total ever held
    released_minor: int  # total ever released
    available_minor: int  # held minus released


class EscrowProvider(Protocol):
    async def hold(self, project_id: uuid.UUID, amount_minor: int, currency: str, ref: str) -> HoldResult: ...

    async def release(self, hold_ref: str, payee: str, amount_minor: int, ref: str) -> ReleaseResult: ...

    async def balance(self, project_id: uuid.UUID) -> Balance: ...


class EscrowProviderError(AppError):
    """The partner could not be reached or refused for a transient reason; safe to retry with the same ref."""

    def __init__(self, message: str = "The escrow provider is unavailable. Try again later.") -> None:
        super().__init__("escrow_provider_unavailable", message, 502)


@dataclass
class _Hold:
    project_id: uuid.UUID
    currency: str
    amount_minor: int
    released_minor: int = 0


def _provider_ref(prefix: str, ref: str) -> str:
    return f"{prefix}_{hashlib.sha256(ref.encode()).hexdigest()[:24]}"


def _check_amount(amount_minor: int) -> None:
    if type(amount_minor) is not int or amount_minor <= 0:
        raise AppError(
            "escrow_invalid_amount", f"amount_minor must be a positive integer, got {amount_minor!r}.", 422
        )


class SimulatedEscrow:
    """In-memory escrow partner for local, staging and the demo.

    Deterministic (provider refs are a hash of our ref), idempotent on ref, never releases more
    than a hold has left. State lives in this process only.

    Test hook: `fail_next("release", times=2)` makes the next two release calls raise
    EscrowProviderError without changing anything, so retries can be tested.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._holds: dict[str, _Hold] = {}
        self._hold_results: dict[str, HoldResult] = {}
        self._release_results: dict[str, ReleaseResult] = {}
        self._project_currency: dict[uuid.UUID, str] = {}
        self._failures: dict[Operation, int] = {}

    def fail_next(self, operation: Operation, times: int = 1) -> None:
        self._failures[operation] = self._failures.get(operation, 0) + times

    def _maybe_fail(self, operation: Operation) -> None:
        remaining = self._failures.get(operation, 0)
        if remaining > 0:
            self._failures[operation] = remaining - 1
            raise EscrowProviderError(f"Simulated escrow failure on {operation}.")

    async def hold(self, project_id: uuid.UUID, amount_minor: int, currency: str, ref: str) -> HoldResult:
        self._maybe_fail("hold")
        _check_amount(amount_minor)
        if not _CURRENCY.match(currency):
            raise AppError("escrow_invalid_currency", f"currency must be ISO 4217, got {currency!r}.", 422)

        if (previous := self._hold_results.get(ref)) is not None:
            if (previous.project_id, previous.amount_minor, previous.currency) != (
                project_id,
                amount_minor,
                currency,
            ):
                raise AppError(
                    "escrow_ref_conflict", f"Hold ref {ref!r} was already used with other details.", 409
                )
            return previous

        project_currency = self._project_currency.get(project_id)
        if project_currency is not None and project_currency != currency:
            raise AppError(
                "escrow_currency_mismatch",
                f"This project's escrow is in {project_currency}, not {currency}.",
                422,
            )

        result = HoldResult(
            provider_ref=_provider_ref("simhold", ref),
            status="held",
            project_id=project_id,
            amount_minor=amount_minor,
            currency=currency,
            ref=ref,
        )
        self._project_currency[project_id] = currency
        self._holds[result.provider_ref] = _Hold(project_id, currency, amount_minor)
        self._hold_results[ref] = result
        return result

    async def release(self, hold_ref: str, payee: str, amount_minor: int, ref: str) -> ReleaseResult:
        self._maybe_fail("release")
        _check_amount(amount_minor)
        if not payee:
            raise AppError("escrow_invalid_payee", "payee is required.", 422)

        if (previous := self._release_results.get(ref)) is not None:
            if (previous.hold_ref, previous.payee, previous.amount_minor) != (hold_ref, payee, amount_minor):
                raise AppError(
                    "escrow_ref_conflict", f"Release ref {ref!r} was already used with other details.", 409
                )
            return previous

        held = self._holds.get(hold_ref)
        if held is None:
            raise AppError("escrow_hold_not_found", f"No hold {hold_ref!r}.", 404)
        left = held.amount_minor - held.released_minor
        if amount_minor > left:
            raise AppError(
                "escrow_insufficient_funds",
                f"Cannot release {amount_minor}; only {left} {held.currency} is left on this hold.",
                422,
            )

        held.released_minor += amount_minor
        result = ReleaseResult(
            provider_ref=_provider_ref("simrel", ref),
            status="released",
            hold_ref=hold_ref,
            payee=payee,
            amount_minor=amount_minor,
            currency=held.currency,
            ref=ref,
        )
        self._release_results[ref] = result
        return result

    async def balance(self, project_id: uuid.UUID) -> Balance:
        self._maybe_fail("balance")
        holds = [h for h in self._holds.values() if h.project_id == project_id]
        held = sum(h.amount_minor for h in holds)
        released = sum(h.released_minor for h in holds)
        return Balance(
            project_id=project_id,
            currency=self._project_currency.get(project_id),
            held_minor=held,
            released_minor=released,
            available_minor=held - released,
        )


@lru_cache
def _provider(name: str) -> EscrowProvider:
    if name == "simulated":
        return SimulatedEscrow()
    raise AppError("escrow_provider_not_configured", f"Unknown ESCROW_PROVIDER {name!r}.", 500)


def get_escrow_provider() -> EscrowProvider:
    """The escrow provider chosen by ESCROW_PROVIDER. One instance per process."""
    return _provider(get_escrow_settings().escrow_provider)
