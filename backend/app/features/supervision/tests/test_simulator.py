"""scripts/simulator.py (owner: James). Lives here because pytest only collects app/ and tests/.

Seeded random.Random keeps these runs repeatable; it draws fake photos, nothing secret.
The full run goes through the real app; then Abigail's real evidence checks must accept every photo.
"""

import random
import uuid
from datetime import UTC, datetime

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service as users
from app.base.users.models import User
from app.core.config import get_settings
from app.features.evidence import checks, signing
from app.features.evidence import service as evidence_service
from app.features.evidence import storage as evidence_storage
from app.features.evidence.hashing import REUSE_MAX_DISTANCE, compute_phash, hamming
from app.features.supervision import service as supervision
from scripts import seed, simulator


def test_payload_matches_the_signing_md_test_vector() -> None:
    built = simulator.payload(
        "a" * 64,
        datetime(2026, 10, 12, 9, 30, 15, 123000, tzinfo=UTC),
        datetime(2026, 10, 12, 9, 30, 14, 900000, tzinfo=UTC),
        6.4595,
        7.50045,
        8.5,
        "11111111-2222-3333-4444-555555555555",
        "device-abc",
    )

    assert built == (
        b"ibh-evidence-v1|" + b"a" * 64 + b"|2026-10-12T09:30:15.123Z|2026-10-12T09:30:14.900Z"
        b"|6.459500|7.500450|8.5|11111111-2222-3333-4444-555555555555|device-abc"
    )


def test_the_phone_signs_what_the_server_verifies() -> None:
    phone = simulator.Phone(device_id="sim-test")
    data = b"ibh-evidence-v1|example"

    assert signing.verify_signature(phone.public_key_b64, data, phone.sign(data))
    assert not signing.verify_signature(phone.public_key_b64, data + b"!", phone.sign(data))


def test_simulated_photos_never_look_reused() -> None:
    rng = random.Random(7)  # noqa: S311
    hashes = [compute_phash(simulator.site_photo(rng)) for _ in range(6)]

    distances = [hamming(a, b) for i, a in enumerate(hashes) for b in hashes[i + 1 :]]
    assert min(distances) > REUSE_MAX_DISTANCE


def test_simulator_refuses_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "environment", "production")

    with pytest.raises(SystemExit, match="production"):
        simulator.refuse_production()


class FakeStorage:
    """Stands in for SeaweedFS/S3: keeps what the simulator PUTs to the pre-signed URLs, and answers
    the evidence service's "is the file there?" and "give me its bytes" questions."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.files: dict[str, bytes] = {}
        monkeypatch.setattr(evidence_storage, "head_object", self.head)
        monkeypatch.setattr(evidence_storage, "read_object", self.files.get)

    def head(self, key: str) -> tuple[int, str] | None:
        return (len(self.files[key]), "image/jpeg") if key in self.files else None

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.method == "PUT"
        key = request.url.path.split(f"/{get_settings().storage_bucket}/", 1)[1]
        self.files[key] = request.content
        return httpx.Response(200)


async def seeded_people(session: AsyncSession) -> dict[str, User]:
    people = {s.key: await seed.upsert_user(session, s) for s in seed.USERS}
    for key, reg in (("supervisor", "SIM-1"), ("supervisor_2", "SIM-2")):
        if not await supervision.is_vetted(session, people[key].id):
            await seed.vet_supervisor(session, people[key], people["ops"], reg)
    for project_seed in seed.PROJECTS:
        await seed.upsert_project(session, project_seed, people)
    return people


async def test_full_run_makes_projects_active_and_every_photo_passes_the_real_checks(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    people = await seeded_people(db_session)
    queued: list[uuid.UUID] = []
    monkeypatch.setattr(evidence_service, "enqueue_run_checks", queued.append)
    store = FakeStorage(monkeypatch)

    async with httpx.AsyncClient(transport=httpx.MockTransport(store.handle)) as storage:
        rng = random.Random(11)  # noqa: S311
        summary = await simulator.simulate(client, storage, people, photos=2, rng=rng)

    assert len(queued) == 2 * len(seed.PROJECTS) == len(store.files)
    # Abigail's checks, for real: file hash, signature, device owner, clock, geofence, reuse.
    for evidence_id in queued:
        evidence = await checks.run_checks(db_session, evidence_id)
        assert (evidence.status, evidence.reject_reason) == ("accepted", None)

    for project_seed in seed.PROJECTS:
        page = await client.get(
            "/api/v1/projects?limit=100",
            headers={"Authorization": f"Bearer {users.create_access_token(people['client'])}"},
        )
        status = next(p["status"] for p in page.json()["items"] if p["title"] == project_seed.title)
        assert status == "active"
    assert len(summary.done) == 3 * len(seed.PROJECTS)
    assert any("Stripe" in line for line in summary.skipped)


async def test_running_twice_is_safe(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    people = await seeded_people(db_session)
    monkeypatch.setattr(evidence_service, "enqueue_run_checks", lambda _id: None)
    store = FakeStorage(monkeypatch)

    async with httpx.AsyncClient(transport=httpx.MockTransport(store.handle)) as storage:
        await simulator.simulate(client, storage, people, photos=1)
        second = await simulator.simulate(client, storage, people, photos=1)

    assert any("already approved" in line for line in second.skipped)  # BoQ isn't redone
    assert len(store.files) == 2 * len(seed.PROJECTS)  # each run adds new captures
