"""The outside world for the backend gate test, faked at its edges. Owner: Christopher.

Everything inside iBackHome runs for real (routes, services, rules, the database, the evidence checks,
the ledger, the simulated escrow partner). Only what lives outside is replaced:

- Stripe Checkout (a fake gateway) and signed Stripe / Paystack webhooks (test secrets);
- Paystack transfers (a fake client) and bank-account registration (seed.py's stand-in);
- object storage for photos (kept in memory) and report PDFs (not rendered);
- the messaging providers (fake adapters: login codes and messages are read from them);
- Celery: jobs are captured when queued, and the test runs them itself in order;
- the AI model (the quote checker gets a fake one; the report agent falls back to its plain summary).
"""

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest
from google import genai

from app.base.notifications import service as notifications_service
from app.base.notifications.adapters import FakeAdapter
from app.base.notifications.models import Channel
from app.base.payments import service as payments_service
from app.base.payments.stripe_checkout import get_checkout_gateway
from app.base.payments.tests.webhook_helpers import webhook_secrets
from app.core.config import get_settings
from app.features.escrow import service as escrow_service
from app.features.escrow.tests.factories import FakeCheckout, funding_settings, simulated_escrow
from app.features.escrow.tests.release_helpers import FakePaystack
from app.features.evidence import service as evidence_service
from app.features.evidence import storage as evidence_storage
from app.features.milestones import notices
from app.features.reports import pdf as report_pdf
from app.features.reports import storage as report_storage


@dataclass
class Jobs:
    """Celery jobs that would have been queued after each commit, in order."""

    checks: list[uuid.UUID] = field(default_factory=list)  # evidence.run_checks
    releases: list[uuid.UUID] = field(default_factory=list)  # escrow.submit_release
    payouts: list[uuid.UUID] = field(default_factory=list)  # payments.send_transfer
    messages: list[tuple[uuid.UUID, str, str]] = field(default_factory=list)  # milestones.send_update


class PhotoStore:
    """Object storage: keeps what is PUT to the pre-signed URLs and answers the evidence service."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.files: dict[str, bytes] = {}
        monkeypatch.setattr(evidence_storage, "head_object", self.head)
        monkeypatch.setattr(evidence_storage, "read_object", self.files.get)
        monkeypatch.setattr(evidence_storage, "presign_read", lambda key, **_: f"https://files.test/{key}")

    def head(self, key: str) -> tuple[int, str] | None:
        return (len(self.files[key]), "image/jpeg") if key in self.files else None

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.method == "PUT"
        key = request.url.path.split(f"/{get_settings().storage_bucket}/", 1)[1]
        self.files[key] = request.content
        return httpx.Response(200)


@dataclass
class World:
    """The fakes a test reads from or steers."""

    jobs: Jobs
    channels: dict[Channel, FakeAdapter]
    checkout: FakeCheckout
    paystack: FakePaystack
    photos: PhotoStore
    storage_http: httpx.AsyncClient

    def sent_to(self, *addresses: str | None) -> list[str]:
        """Every message text that reached any of these phones or emails, in channel order."""
        wanted = {a for a in addresses if a}
        return [m.text for adapter in self.channels.values() for to, m in adapter.sent if to in wanted]


@pytest.fixture
async def outside(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[World]:
    from app.main import app

    with webhook_secrets(monkeypatch):
        settings = funding_settings(monkeypatch)
        next(settings)

        jobs = Jobs()
        monkeypatch.setattr(evidence_service, "enqueue_run_checks", jobs.checks.append)
        monkeypatch.setattr(escrow_service, "enqueue_submit_release", jobs.releases.append)
        monkeypatch.setattr(payments_service, "enqueue_send_transfer", jobs.payouts.append)
        monkeypatch.setattr(notices, "enqueue_update", lambda m, e, k: jobs.messages.append((m, e, k)))

        channels = {channel: FakeAdapter() for channel in Channel}
        monkeypatch.setattr(notifications_service, "get_adapters", lambda: channels)

        checkout = FakeCheckout()
        app.dependency_overrides[get_checkout_gateway] = lambda: checkout
        paystack = FakePaystack()
        monkeypatch.setattr(payments_service, "get_paystack_client", lambda: paystack)

        monkeypatch.setattr(report_pdf, "render_pdf", lambda body, **_: b"%PDF-1.7 " + body.encode()[:20])
        monkeypatch.setattr(report_storage, "put_pdf", lambda key, data: None)
        monkeypatch.setattr(report_storage, "presign_read", lambda key: f"https://files.test/{key}")

        def never_call_gemini(*_: Any, **__: Any) -> None:
            raise RuntimeError("the gate test must not call the real Gemini API")

        monkeypatch.setattr(genai, "Client", never_call_gemini)

        simulated_escrow().reset()
        photos = PhotoStore(monkeypatch)
        async with httpx.AsyncClient(transport=httpx.MockTransport(photos.handle)) as storage_http:
            try:
                yield World(jobs, channels, checkout, paystack, photos, storage_http)
            finally:
                app.dependency_overrides.pop(get_checkout_gateway, None)
                simulated_escrow().reset()
                next(settings, None)
