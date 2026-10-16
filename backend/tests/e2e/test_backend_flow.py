"""The backend done gate (team task doc, "Backend done gate"), run through the API. Owner: Christopher.

Each test drives the real app over HTTP as the people involved, signing in with one-time codes, and
checks what the gate asks for. Outside services are faked at their edges (see conftest.py); background
jobs are run by the test in the order Celery would run them.

    uv run pytest tests/e2e -v          # locally (needs the database), or inside the api container

The gate's last two boxes are checked elsewhere: CI is green, and scripts/seed.py + simulator.py have
their own tests (agents/tests, supervision/tests/test_simulator.py).
"""

import hashlib
import json
import random
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi.routing import APIRoute
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base import payments
from app.base.notifications.models import Channel
from app.base.payments.models import LedgerEntry, PaymentEvent, Payout
from app.base.payments.tasks import run_send_transfer
from app.base.users.models import User
from app.features.agents import report_agent
from app.features.agents import service as agents
from app.features.agents.llm import LLMClient, LLMSettings
from app.features.escrow.tasks import run_submit_release
from app.features.escrow.tests.factories import completed_event, send_stripe
from app.features.escrow.tests.release_helpers import (
    send_paystack,
    session_factory,
    transfer_event,
    unbalanced,
)
from app.features.evidence import checks
from app.features.milestones import notices
from app.features.price_index import service as price_index
from app.features.price_index.schemas import SurveyRow
from app.features.quotes.router import get_quote_llm
from app.features.quotes.tests.test_check import PARSED, QUOTE_LINES, _FakeGemini, pdf_body
from app.features.reports import service as reports
from app.features.suppliers import service as suppliers
from scripts import seed, simulator
from tests.e2e.conftest import World

API = "/api/v1"
ENUGU = (6.4500, 7.5000)  # the site pin (Independence Layout)
SUPPLIER_NAME = "Gate Test Building Supplies"


# --- people and the API ------------------------------------------------------------------------


class Person:
    def __init__(self, user: User, token: str) -> None:
        self.user = user
        self.token = token

    @property
    def id(self) -> uuid.UUID:
        return self.user.id


class Gate:
    """The API as the people in the gate use it."""

    def __init__(self, client: AsyncClient, db: AsyncSession, world: World) -> None:
        self.client = client
        self.db = db
        self.world = world

    async def call(
        self, method: str, path: str, who: Person | None, body: Any = None, *, expect: int = 200
    ) -> Any:
        headers = {"Idempotency-Key": uuid.uuid4().hex} if method != "GET" else {}
        if who is not None:
            headers["Authorization"] = f"Bearer {who.token}"
        response = await self.client.request(method, API + path, json=body, headers=headers)
        assert response.status_code == expect, f"{method} {path}: {response.status_code} {response.text}"
        return response.json() if response.content else None

    async def sign_in(self, identifier: str, channel: str) -> Person:
        """OTP sign-in: request a code, read it from the message the person received, verify it."""
        await self.call(
            "POST", "/auth/otp/request", None, {"identifier": identifier, "channel": channel}, expect=202
        )
        [(to, message)] = self.world.channels[Channel(channel)].sent[-1:]
        assert to == identifier
        code = re.search(r"\b(\d{6})\b", message.text)
        assert code is not None, message.text
        tokens = await self.call(
            "POST", "/auth/otp/verify", None, {"identifier": identifier, "code": code.group(1)}
        )
        me = await self.client.get(f"{API}/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
        user = await self.db.get(User, uuid.UUID(me.json()["id"]))
        assert user is not None
        return Person(user, tokens["access_token"])

    async def seeded(self, role: str, name: str) -> Person:
        """Supervisors and ops come from seeding (spec: roles), then sign in like anyone else."""
        phone = f"+234803{secrets.randbelow(10**7):07d}"
        self.db.add(User(phone=phone, role=role, status="active", full_name=name))
        await self.db.flush()
        return await self.sign_in(phone, "sms")


async def run_jobs(gate: Gate) -> None:
    """Run what Celery would have run after the commits so far, until nothing is left."""
    jobs, db = gate.world.jobs, gate.db
    factory = session_factory(db)
    while jobs.checks or jobs.releases or jobs.payouts:
        while jobs.checks:
            await checks.run_checks(db, jobs.checks.pop(0))
        while jobs.releases:
            assert await run_submit_release(factory, jobs.releases.pop(0), retries=0) == "done"
        while jobs.payouts:
            payout_id = jobs.payouts.pop(0)
            await run_send_transfer(factory, payout_id, retries=0)
            payout = await db.get(Payout, payout_id)
            assert payout is not None
            await db.refresh(payout)
            response = await send_paystack(gate.client, transfer_event("transfer.success", payout))
            assert response.status_code == 200


async def deliver_messages(gate: Gate) -> list[str]:
    """Run the queued milestones.send_update jobs; returns the events in the order they were queued."""
    events = []
    while gate.world.jobs.messages:
        milestone_id, event, key = gate.world.jobs.messages.pop(0)
        await notices.send_update(gate.db, milestone_id, event, key)
        events.append(event)
    return events


# --- the setup every gate check starts from ----------------------------------------------------


class Site:
    def __init__(self, project: dict[str, Any], milestones: list[dict[str, Any]], **people: Person) -> None:
        self.project = project
        self.id = project["id"]
        self.milestones = milestones
        self.client: Person = people["client"]
        self.contractor: Person = people["contractor"]
        self.supervisor: Person = people["supervisor"]
        self.ops: Person = people["ops"]
        self.ops_2: Person = people["ops_2"]
        self.phone = simulator.Phone(device_id=f"gate-{uuid.uuid4().hex[:8]}")


async def project_ready_to_build(gate: Gate) -> Site:
    """Gate, full flow, boxes 1-3: OTP sign-in, project, site, BoQ approved by three, supervisor."""
    client = await gate.sign_in(f"{secrets.token_hex(4)}.client@example.com", "email")  # abroad: email
    contractor_phone = f"+234803{secrets.randbelow(10**7):07d}"
    project = await gate.call(
        "POST",
        "/projects",
        client,
        {
            "title": f"Gate bungalow {secrets.token_hex(3)}",
            "address": "Independence Layout, Enugu",
            "currency": "NGN",
            "budget_minor": 40_000_000_00,
            "contractor_phone": contractor_phone,
        },
        expect=201,
    )
    pid = project["id"]
    await gate.call(
        "PUT",
        f"/projects/{pid}/site",
        client,
        {"location": {"lat": ENUGU[0], "lon": ENUGU[1]}, "geofence": seed.square_fence(*ENUGU)},
    )

    contractor = await gate.sign_in(contractor_phone, "sms")  # invited: lands on the contractor account
    assert contractor.user.role == "contractor"
    ops, ops_2 = await gate.seeded("ops", "Gate Ops"), await gate.seeded("ops", "Gate Ops Two")

    await gate.call("PUT", f"/projects/{pid}/boq", contractor, simulator.BOQ)
    for who in (client, contractor, ops):
        await gate.call("POST", f"/projects/{pid}/boq/approve", who)
    assert (await gate.call("GET", f"/projects/{pid}", client))["status"] == "active"
    milestones = await gate.call("GET", f"/projects/{pid}/milestones", client)
    assert [m["name"] for m in milestones] == ["Foundation", "Blockwork to lintel", "Roofing"]
    assert {m["status"] for m in milestones} == {"pending"}

    supervisor = await gate.seeded("supervisor", "Gate Supervisor")
    await gate.call(
        "PUT",
        "/supervisors/me/profile",
        supervisor,
        {
            "registration_body": "COREN",
            "registration_no": f"GATE-{secrets.token_hex(3)}",
            "guarantor_1": "Ngozi Eze, +2348030000101",
            "guarantor_2": "Emeka Obi, +2348030000102",
            "related_contractors": [],
        },
    )
    await gate.call(
        "POST",
        f"/supervisors/{supervisor.id}/vetting",
        ops,
        {
            "decision": "approved",
            "registration_verified": True,
            "nin_verified": True,
            "guarantor_1_verified": True,
            "guarantor_2_verified": True,
        },
    )
    await gate.call("POST", f"/projects/{pid}/supervisor", ops, {"supervisor_id": str(supervisor.id)})

    site = Site(
        project, milestones, client=client, contractor=contractor, supervisor=supervisor, ops=ops, ops_2=ops_2
    )
    await gate.call(
        "POST",
        "/devices",
        supervisor,
        {"device_id": site.phone.device_id, "public_key": site.phone.public_key_b64},
        expect=201,
    )
    # The contractor's bank account (normally registered by ops; seed.py's stand-in for Paystack).
    await payments.register_payout_recipient(
        gate.db,
        account_name="Gate Contractor",
        account_number=f"{secrets.randbelow(10**10):010d}",
        bank_code="057",
        actor_id=ops.id,
        user_id=contractor.id,
        client=seed.StandInPaystack(),
    )
    return site


async def fund(gate: Gate, site: Site, milestone: dict[str, Any]) -> dict[str, Any]:
    """Gate box 4: the client pays by Stripe (test), Stripe's signed webhook comes back."""
    checkout = await gate.call(
        "POST",
        f"/projects/{site.id}/funding",
        site.client,
        {"milestone_id": milestone["id"], "currency": "GBP"},
        expect=201,
    )
    event = completed_event(gate.world.checkout.requests[-1], checkout["checkout_session_id"])
    assert (await send_stripe(gate.client, event)).status_code == 200
    return event


async def capture(
    gate: Gate,
    site: Site,
    *,
    milestone: dict[str, Any] | None = None,
    photo: bytes | None = None,
    offset_deg: float = 0.0,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Gate box 5: a signed capture from the in-app camera, uploaded and submitted, then checked."""
    rng = rng or random.Random()  # noqa: S311 - fake photo pixels, not a secret
    photo = photo or simulator.site_photo(rng)
    sha256 = hashlib.sha256(photo).hexdigest()
    lat, lon = ENUGU[0] + offset_deg, ENUGU[1]
    captured_at = datetime.now(UTC) - timedelta(minutes=2)
    gps_time = captured_at - timedelta(milliseconds=400)
    slot = await gate.call(
        "POST",
        "/evidence/upload-url",
        site.supervisor,
        {"project_id": site.id, "kind": "photo", "content_type": "image/jpeg"},
        expect=200,
    )
    put = await gate.world.storage_http.put(
        slot["upload_url"], content=photo, headers=slot.get("headers") or {}
    )
    assert put.status_code == 200
    signed = simulator.payload(sha256, captured_at, gps_time, lat, lon, 6.0, site.id, site.phone.device_id)
    evidence = await gate.call(
        "POST",
        "/evidence",
        site.supervisor,
        {
            "project_id": site.id,
            "kind": "photo",
            "storage_key": slot["storage_key"],
            "file_sha256": sha256,
            "captured_at": captured_at.isoformat(),
            "gps_time": gps_time.isoformat(),
            "latitude": lat,
            "longitude": lon,
            "accuracy_m": 6.0,
            "device_id": site.phone.device_id,
            "signature": site.phone.sign(signed),
            "milestone_id": milestone["id"] if milestone else None,
        },
        expect=201,
    )
    await run_jobs(gate)  # evidence.run_checks
    page = await gate.call("GET", f"/projects/{site.id}/evidence?limit=100", site.ops)
    checked: dict[str, Any] = next(e for e in page["items"] if e["id"] == evidence["id"])
    return checked


async def claim_and_verify(gate: Gate, site: Site, milestone: dict[str, Any], evidence_id: str) -> None:
    await gate.call("POST", f"/milestones/{milestone['id']}/claim", site.contractor)
    await gate.call(
        "POST",
        f"/milestones/{milestone['id']}/verify",
        site.supervisor,
        {
            "decision": "verified",
            "checklist": [{"item": "Work matches the BoQ", "passed": True, "evidence_ids": [evidence_id]}],
        },
    )


async def status_of(gate: Gate, site: Site, milestone: dict[str, Any]) -> str:
    milestones = await gate.call("GET", f"/projects/{site.id}/milestones", site.client)
    return str(next(m["status"] for m in milestones if m["id"] == milestone["id"]))


async def ledger_is_balanced(gate: Gate) -> None:
    entries = list(await gate.db.scalars(select(LedgerEntry)))
    assert unbalanced(entries) == {}


# --- the full flow -----------------------------------------------------------------------------


async def test_full_flow_from_sign_in_to_released(
    client: AsyncClient, db_session: AsyncSession, outside: World
) -> None:
    gate = Gate(client, db_session, outside)
    site = await project_ready_to_build(gate)
    foundation = site.milestones[0]

    await fund(gate, site, foundation)
    assert await status_of(gate, site, foundation) == "funded"
    await ledger_is_balanced(gate)

    photo = await capture(gate, site, milestone=foundation)
    assert (photo["status"], photo.get("reject_reason")) == ("accepted", None)

    await claim_and_verify(gate, site, foundation, photo["id"])
    await gate.call("POST", f"/milestones/{foundation['id']}/approve", site.client)
    assert await status_of(gate, site, foundation) == "approved"
    await run_jobs(gate)  # escrow.submit_release -> released -> contractor payout -> Paystack success
    assert await status_of(gate, site, foundation) == "released"
    await ledger_is_balanced(gate)
    payout = await db_session.scalar(select(Payout).order_by(Payout.created_at.desc()).limit(1))
    assert payout is not None and payout.status == "success"

    # Extras: notifications arrive for claim, verify and release (the client signs in by email).
    assert await deliver_messages(gate) == ["claimed", "verified", "released"]
    to_client = outside.sent_to(site.client.user.email)
    assert any("says 'Foundation'" in text for text in to_client)
    assert any("verified 'Foundation'" in text for text in to_client)
    assert any("has been released to your contractor" in text for text in to_client)
    assert any("released to you" in text for text in outside.sent_to(site.contractor.user.phone))

    # Protection: every write appears in the audit log (ops reads it through the API).
    for object_id, expected in (
        (
            foundation["id"],
            {
                "milestone.funded",
                "milestone.claimed",
                "milestone.verified",
                "milestone.approved",
                "milestone.released",
            },
        ),
        (
            site.id,
            {"project.created", "boq.submitted", "boq.approved", "project.supervisor_assigned"},
        ),
        (photo["id"], {"evidence.submitted", "evidence.accepted"}),
    ):
        page = await gate.call("GET", f"/ops/audit?object_id={object_id}&limit=200", site.ops)
        actions = {entry["action"] for entry in page["items"]}
        assert expected <= actions, f"{object_id}: missing {expected - actions}"
    # The site is its own object; its entry names the project.
    sites = await gate.call("GET", "/ops/audit?action=site.set&limit=200", site.ops)
    assert any(entry["after"]["project_id"] == site.id for entry in sites["items"])


# --- the protections ---------------------------------------------------------------------------


async def test_outside_photo_rejected_and_reused_photo_flagged(
    client: AsyncClient, db_session: AsyncSession, outside: World
) -> None:
    gate = Gate(client, db_session, outside)
    site = await project_ready_to_build(gate)

    outside_photo = await capture(gate, site, offset_deg=0.01)  # about 1 km from the site
    assert outside_photo["status"] == "rejected" and outside_photo["reject_reason"]

    original = simulator.site_photo(random.Random(7))  # noqa: S311
    assert (await capture(gate, site, photo=original))["status"] == "accepted"
    assert (await capture(gate, site, photo=original))["status"] == "flagged"


async def test_a_dispute_blocks_release_until_two_ops_users_resolve_it(
    client: AsyncClient, db_session: AsyncSession, outside: World
) -> None:
    gate = Gate(client, db_session, outside)
    site = await project_ready_to_build(gate)
    foundation = site.milestones[0]
    await fund(gate, site, foundation)
    photo = await capture(gate, site, milestone=foundation)
    await claim_and_verify(gate, site, foundation, photo["id"])

    dispute = await gate.call(
        "POST",
        f"/milestones/{foundation['id']}/disputes",
        site.client,
        {"reason": "Cracks in the footing"},
        expect=201,
    )
    assert await status_of(gate, site, foundation) == "disputed"
    await gate.call("POST", f"/milestones/{foundation['id']}/approve", site.client, expect=409)  # no release
    assert outside.jobs.releases == []

    body = {"outcome": "release", "notes": "Engineer confirmed the footing is sound"}
    first = await gate.call("POST", f"/disputes/{dispute['id']}/resolve", site.ops, body)
    assert first["resolved"] is False and outside.jobs.releases == []  # one ops user isn't enough
    await gate.call("POST", f"/disputes/{dispute['id']}/resolve", site.ops, body, expect=409)  # nor twice
    second = await gate.call("POST", f"/disputes/{dispute['id']}/resolve", site.ops_2, body)
    assert second["resolved"] is True and second["release_id"]

    await run_jobs(gate)
    assert await status_of(gate, site, foundation) == "released"
    await ledger_is_balanced(gate)


async def test_the_same_stripe_webhook_twice_creates_one_payment(
    client: AsyncClient, db_session: AsyncSession, outside: World
) -> None:
    gate = Gate(client, db_session, outside)
    site = await project_ready_to_build(gate)
    event = await fund(gate, site, site.milestones[0])
    entries_before = len(list(await db_session.scalars(select(LedgerEntry))))

    assert (await send_stripe(client, event)).status_code == 200  # Stripe re-delivers

    stored = list(await db_session.scalars(select(PaymentEvent).where(PaymentEvent.event_id == event["id"])))
    assert len(stored) == 1
    assert len(list(await db_session.scalars(select(LedgerEntry)))) == entries_before
    assert await status_of(gate, site, site.milestones[0]) == "funded"


async def test_strangers_get_403_and_agents_cannot_approve_release_or_pay(
    client: AsyncClient, db_session: AsyncSession, outside: World
) -> None:
    gate = Gate(client, db_session, outside)
    site = await project_ready_to_build(gate)
    foundation = site.milestones[0]
    stranger = await gate.sign_in(f"{secrets.token_hex(4)}.stranger@example.com", "email")
    for path in (f"/projects/{site.id}", f"/projects/{site.id}/milestones", f"/projects/{site.id}/boq"):
        await gate.call("GET", path, stranger, expect=403)

    agent_user = await seed.upsert_agent_user(db_session, report_agent.AGENT_NAME)
    every_route = [r.path for r in client._transport.app.routes if isinstance(r, APIRoute)]  # type: ignore[attr-defined]
    token = agents.create_service_token(report_agent.AGENT_NAME, every_route, user_id=agent_user.id)
    agent = Person(agent_user, token)
    for method, path, body in (
        ("POST", f"/milestones/{foundation['id']}/approve", None),
        ("POST", f"/projects/{site.id}/funding", {"milestone_id": foundation["id"], "currency": "GBP"}),
        ("POST", f"/projects/{site.id}/boq/approve", None),
    ):
        await gate.call(method, path, agent, body, expect=403)  # even with every route on its list


# --- the extras --------------------------------------------------------------------------------


async def test_quote_checker_flags_an_inflated_line(
    client: AsyncClient, db_session: AsyncSession, outside: World
) -> None:
    from app.main import app

    gate = Gate(client, db_session, outside)
    site = await project_ready_to_build(gate)
    today = datetime.now(UTC).date()
    await price_index.load_survey(
        db_session,
        [
            SurveyRow(
                item="Cement (50 kg bag)", unit="bag", price_minor=9_500_00, supplier="A", observed_on=today
            ),
            SurveyRow(item="Sharp sand", unit="trip", price_minor=80_000_00, supplier="A", observed_on=today),
        ],
    )
    fake = _FakeGemini(json.dumps(PARSED))
    llm = LLMClient(LLMSettings(llm_api_key="unused", llm_model="gem-1"), client=fake)  # type: ignore[arg-type]
    app.dependency_overrides[get_quote_llm] = lambda: llm
    try:
        result = await gate.call("POST", "/quotes/check", site.contractor, pdf_body(QUOTE_LINES))
    finally:
        app.dependency_overrides.pop(get_quote_llm, None)

    cement = next(line for line in result["lines"] if line["item"].startswith("Cement"))
    assert cement["flag"] == "over_index" and result["flagged_count"] == 1


async def test_weekly_report_is_generated_reviewed_and_sent(
    client: AsyncClient, db_session: AsyncSession, outside: World
) -> None:
    gate = Gate(client, db_session, outside)
    site = await project_ready_to_build(gate)
    await seed.upsert_agent_user(db_session, report_agent.AGENT_NAME)
    monday = reports.week_start_of(datetime.now(UTC).date())

    outcome = await report_agent.generate_weekly_report(db_session, uuid.UUID(site.id), monday)
    [draft] = [r for r in await gate.call("GET", f"/projects/{site.id}/reports", site.client)]
    assert draft["id"] == str(outcome.report.id) and draft["status"] == "draft"

    reviewed = await gate.call("POST", f"/reports/{draft['id']}/review", site.supervisor)
    assert reviewed["status"] == "reviewed" and reviewed["pdf_url"]
    assert await reports.send_reviewed(db_session) >= 1

    [sent] = [r for r in await gate.call("GET", f"/projects/{site.id}/reports", site.client)]
    assert sent["status"] == "sent"
    assert any("weekly report" in text for text in outside.sent_to(site.client.user.email))


async def test_supplier_order_is_approved_delivered_and_paid(
    client: AsyncClient, db_session: AsyncSession, outside: World
) -> None:
    gate = Gate(client, db_session, outside)
    site = await project_ready_to_build(gate)
    await fund(gate, site, site.milestones[0])  # the order is paid from the project's escrow money
    photo = await capture(gate, site, milestone=site.milestones[0])

    supplier_user = await gate.seeded("supplier", SUPPLIER_NAME)
    supplier = await suppliers.ensure_supplier(
        db_session, SUPPLIER_NAME, owner_id=supplier_user.id, verified=True, actor_id=site.ops.id
    )
    await payments.register_payout_recipient(
        db_session,
        account_name=SUPPLIER_NAME,
        account_number=f"{secrets.randbelow(10**10):010d}",
        bank_code="057",
        actor_id=site.ops.id,
        supplier_id=supplier.id,
        client=seed.StandInPaystack(),
    )

    order = await gate.call(
        "POST",
        f"/projects/{site.id}/orders",
        site.contractor,
        {
            "supplier_id": str(supplier.id),
            "items": [
                {"item": "Cement (50 kg bag)", "unit": "bag", "quantity": "100", "unit_price_minor": 9_800_00}
            ],
        },
        expect=201,
    )
    await gate.call("POST", f"/orders/{order['id']}/approve", site.client)
    await gate.call(
        "POST",
        f"/orders/{order['id']}/delivery",
        site.supervisor,
        {"quantities": [{"item": "Cement (50 kg bag)", "quantity": "100"}], "evidence_ids": [photo["id"]]},
        expect=201,
    )
    await run_jobs(gate)  # supplier release -> Paystack payout -> success webhook

    paid = await suppliers.get_order(db_session, uuid.UUID(order["id"]))
    await db_session.refresh(paid)
    assert paid.status == "paid"
    assert paid.total_minor == int(Decimal("100") * 9_800_00)
    await ledger_is_balanced(gate)


# --- ready for the web phase -------------------------------------------------------------------


async def test_every_endpoint_appears_in_the_api_docs(client: AsyncClient) -> None:
    """Every route of every feature's router.py (as main.py mounts them under /api/v1) is in /docs."""
    from fastapi import APIRouter

    from app.core.discovery import import_all

    documented = set((await client.get("/openapi.json")).json()["paths"])
    routes = {
        API + route.path
        for module in import_all("router")
        if isinstance(router := getattr(module, "router", None), APIRouter)
        for route in router.routes
        if isinstance(route, APIRoute)
    }
    assert len(routes) > 40 and routes <= documented, f"not in /docs: {sorted(routes - documented)}"
