import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.audit.models import AuditEntry
from app.core.config import get_settings
from app.features.evidence import service
from app.features.evidence.models import Evidence
from app.features.evidence.tests.conftest import (
    World,
    bearer,
    evidence_body,
    make_user,
    make_world,
    upload,
)


@pytest.fixture
async def world(db_session: AsyncSession) -> World:
    return await make_world(db_session)


# POST /evidence/upload-url


async def test_supervisor_gets_an_upload_url(client: AsyncClient, world: World) -> None:
    response = await client.post(
        "/api/v1/evidence/upload-url",
        json={"project_id": str(world.project.id), "kind": "photo", "content_type": "image/jpeg"},
        headers=bearer(world.supervisor),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["storage_key"].startswith(f"evidence/{world.project.id}/")
    assert body["storage_key"].endswith(".jpg")
    assert body["max_bytes"] == 10 * 1024 * 1024
    assert body["headers"] == {"Content-Type": "image/jpeg"}
    assert parse_qs(urlparse(body["upload_url"]).query)["X-Amz-Expires"] == ["900"]


async def test_video_url_allows_60_mb(client: AsyncClient, world: World) -> None:
    response = await client.post(
        "/api/v1/evidence/upload-url",
        json={"project_id": str(world.project.id), "kind": "video", "content_type": "video/mp4"},
        headers=bearer(world.contractor),
    )
    assert response.status_code == 200
    assert response.json()["max_bytes"] == 60 * 1024 * 1024
    assert response.json()["storage_key"].endswith(".mp4")


async def test_kind_and_content_type_must_match(client: AsyncClient, world: World) -> None:
    response = await client.post(
        "/api/v1/evidence/upload-url",
        json={"project_id": str(world.project.id), "kind": "video", "content_type": "image/jpeg"},
        headers=bearer(world.supervisor),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_content_type"


async def test_other_content_types_are_refused(client: AsyncClient, world: World) -> None:
    response = await client.post(
        "/api/v1/evidence/upload-url",
        json={"project_id": str(world.project.id), "kind": "photo", "content_type": "application/pdf"},
        headers=bearer(world.supervisor),
    )
    assert response.status_code == 422


async def test_upload_url_needs_project_membership(
    client: AsyncClient, db_session: AsyncSession, world: World
) -> None:
    stranger = await make_user(db_session, "supervisor")
    response = await client.post(
        "/api/v1/evidence/upload-url",
        json={"project_id": str(world.project.id), "kind": "photo", "content_type": "image/jpeg"},
        headers=bearer(stranger),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_project_member"


async def test_client_role_cannot_upload(client: AsyncClient, world: World) -> None:
    response = await client.post(
        "/api/v1/evidence/upload-url",
        json={"project_id": str(world.project.id), "kind": "photo", "content_type": "image/jpeg"},
        headers=bearer(world.client),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_role"


async def test_upload_url_signed_out_is_401(client: AsyncClient, world: World) -> None:
    response = await client.post(
        "/api/v1/evidence/upload-url",
        json={"project_id": str(world.project.id), "kind": "photo", "content_type": "image/jpeg"},
    )
    assert response.status_code == 401


# POST /evidence


async def new_key(client: AsyncClient, world: World, who: Any = None) -> str:
    response = await client.post(
        "/api/v1/evidence/upload-url",
        json={"project_id": str(world.project.id), "kind": "photo", "content_type": "image/jpeg"},
        headers=bearer(who or world.supervisor),
    )
    return str(response.json()["storage_key"])


async def test_submit_saves_pending_checks_and_queues_the_job(
    client: AsyncClient,
    db_session: AsyncSession,
    world: World,
    s3: Any,
    queued: list[uuid.UUID],
) -> None:
    key = await new_key(client, world)
    body = upload(s3, key, size=4096)
    response = await client.post(
        "/api/v1/evidence", json=evidence_body(world, key, body), headers=bearer(world.supervisor)
    )

    assert response.status_code == 201
    out = response.json()
    assert out["status"] == "pending_checks"
    assert out["captured_by"] == str(world.supervisor.id)
    assert out["captured_by_role"] == "supervisor"
    assert out["size_bytes"] == 4096
    assert out["milestone_id"] == str(world.milestone.id)
    row = await db_session.get(Evidence, uuid.UUID(out["id"]))
    assert row is not None and row.signature == "c2lnbmF0dXJl" and row.device_id == "phone-1"
    assert queued == [uuid.UUID(out["id"])]
    entry = await db_session.scalar(select(AuditEntry).where(AuditEntry.object_id == row.id))
    assert entry is not None and entry.action == "evidence.submitted"


async def test_file_must_be_uploaded_first(
    client: AsyncClient, world: World, s3: Any, queued: list[uuid.UUID]
) -> None:
    key = await new_key(client, world)
    response = await client.post(
        "/api/v1/evidence", json=evidence_body(world, key, b"x"), headers=bearer(world.supervisor)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "file_not_uploaded"
    assert queued == []


async def test_oversized_photo_is_refused_and_deleted(
    client: AsyncClient, world: World, s3: Any, queued: list[uuid.UUID]
) -> None:
    key = await new_key(client, world)
    body = upload(s3, key, size=10 * 1024 * 1024 + 1)
    response = await client.post(
        "/api/v1/evidence", json=evidence_body(world, key, body), headers=bearer(world.supervisor)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "file_too_large"
    listed = s3.list_objects_v2(Bucket=get_settings().storage_bucket, Prefix=key)
    assert listed["KeyCount"] == 0
    assert queued == []


async def test_wrong_stored_content_type_is_refused(client: AsyncClient, world: World, s3: Any) -> None:
    key = await new_key(client, world)
    body = upload(s3, key, content_type="application/octet-stream")
    response = await client.post(
        "/api/v1/evidence", json=evidence_body(world, key, body), headers=bearer(world.supervisor)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_content_type"


async def test_storage_key_must_belong_to_the_project(client: AsyncClient, world: World, s3: Any) -> None:
    key = f"evidence/{uuid.uuid4()}/{uuid.uuid4()}.jpg"
    body = upload(s3, key)
    response = await client.post(
        "/api/v1/evidence", json=evidence_body(world, key, body), headers=bearer(world.supervisor)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_storage_key"


async def test_milestone_must_be_on_the_same_project(
    client: AsyncClient, db_session: AsyncSession, world: World, s3: Any
) -> None:
    other = await make_world(db_session)
    key = await new_key(client, world)
    body = upload(s3, key)
    response = await client.post(
        "/api/v1/evidence",
        json=evidence_body(world, key, body, milestone_id=str(other.milestone.id)),
        headers=bearer(world.supervisor),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "milestone_not_in_project"


async def test_unknown_milestone_is_404(client: AsyncClient, world: World, s3: Any) -> None:
    key = await new_key(client, world)
    body = upload(s3, key)
    response = await client.post(
        "/api/v1/evidence",
        json=evidence_body(world, key, body, milestone_id=str(uuid.uuid4())),
        headers=bearer(world.supervisor),
    )
    assert response.status_code == 404


async def test_milestone_is_optional(client: AsyncClient, world: World, s3: Any) -> None:
    key = await new_key(client, world)
    body = upload(s3, key)
    data = evidence_body(world, key, body)
    del data["milestone_id"]
    response = await client.post("/api/v1/evidence", json=data, headers=bearer(world.supervisor))
    assert response.status_code == 201
    assert response.json()["milestone_id"] is None


async def test_non_member_cannot_submit(
    client: AsyncClient, db_session: AsyncSession, world: World, s3: Any
) -> None:
    key = await new_key(client, world)
    body = upload(s3, key)
    stranger = await make_user(db_session, "supervisor")
    response = await client.post(
        "/api/v1/evidence", json=evidence_body(world, key, body), headers=bearer(stranger)
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_project_member"


async def test_client_role_cannot_submit(client: AsyncClient, world: World, s3: Any) -> None:
    key = await new_key(client, world)
    body = upload(s3, key)
    response = await client.post(
        "/api/v1/evidence", json=evidence_body(world, key, body), headers=bearer(world.client)
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "bad",
    [
        {"file_sha256": "ABC"},
        {"latitude": 91},
        {"longitude": -181},
        {"accuracy_m": -1},
        {"captured_at": "2026-10-14T09:30:15"},  # no timezone
        {"kind": "audio"},
    ],
)
async def test_invalid_metadata_is_422(
    client: AsyncClient, world: World, s3: Any, bad: dict[str, Any]
) -> None:
    key = await new_key(client, world)
    body = upload(s3, key)
    response = await client.post(
        "/api/v1/evidence", json=evidence_body(world, key, body, **bad), headers=bearer(world.supervisor)
    )
    assert response.status_code == 422


async def test_submitting_twice_returns_the_same_row_and_queues_once(
    client: AsyncClient, world: World, s3: Any, queued: list[uuid.UUID]
) -> None:
    key = await new_key(client, world)
    body = upload(s3, key)
    data = evidence_body(world, key, body)
    first = await client.post("/api/v1/evidence", json=data, headers=bearer(world.supervisor))
    second = await client.post("/api/v1/evidence", json=data, headers=bearer(world.supervisor))
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert len(queued) == 1


async def test_idempotency_key_replays_the_saved_response(
    client: AsyncClient, world: World, s3: Any, queued: list[uuid.UUID]
) -> None:
    key = await new_key(client, world)
    body = upload(s3, key)
    data = evidence_body(world, key, body)
    headers = bearer(world.supervisor) | {"Idempotency-Key": "capture-1"}
    first = await client.post("/api/v1/evidence", json=data, headers=headers)
    second = await client.post("/api/v1/evidence", json=data, headers=headers)
    assert first.status_code == second.status_code == 201
    assert second.json() == first.json()
    assert len(queued) == 1


async def test_someone_elses_file_is_a_conflict(client: AsyncClient, world: World, s3: Any) -> None:
    key = await new_key(client, world)
    body = upload(s3, key)
    data = evidence_body(world, key, body)
    await client.post("/api/v1/evidence", json=data, headers=bearer(world.supervisor))
    response = await client.post("/api/v1/evidence", json=data, headers=bearer(world.contractor))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "storage_key_taken"


async def test_contractor_evidence_is_labelled_as_contractor(
    client: AsyncClient, world: World, s3: Any
) -> None:
    key = await new_key(client, world, world.contractor)
    body = upload(s3, key)
    response = await client.post(
        "/api/v1/evidence", json=evidence_body(world, key, body), headers=bearer(world.contractor)
    )
    assert response.status_code == 201
    assert response.json()["captured_by_role"] == "contractor"


async def test_a_queue_outage_does_not_lose_the_upload(
    client: AsyncClient,
    db_session: AsyncSession,
    world: World,
    s3: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.features.evidence import tasks

    def broken(_: str) -> None:
        raise ConnectionError("redis is down")

    monkeypatch.setattr(tasks.run_checks, "delay", broken)
    key = await new_key(client, world)
    body = upload(s3, key)
    response = await client.post(
        "/api/v1/evidence", json=evidence_body(world, key, body), headers=bearer(world.supervisor)
    )
    assert response.status_code == 201
    assert await db_session.get(Evidence, uuid.UUID(response.json()["id"])) is not None


# Reading what is in storage.


async def test_head_object_reads_size_and_type(client: AsyncClient, world: World, s3: Any) -> None:
    from app.features.evidence import storage

    key = await new_key(client, world)
    upload(s3, key, size=100)  # the phone's PUT, done straight against the in-memory store
    size, content_type = storage.head_object(key) or (0, "")
    assert (size, content_type) == (100, "image/jpeg")
    assert storage.head_object(f"{key}.missing") is None


# service.accepted_for_milestone, used by milestones to verify


async def add_evidence(
    db_session: AsyncSession, world: World, *, role: str, status: str, milestone: Any = None, n: int = 0
) -> Evidence:
    who = world.supervisor if role == "supervisor" else world.contractor
    row = Evidence(
        project_id=world.project.id,
        milestone_id=(milestone or world.milestone).id,
        captured_by=who.id,
        captured_by_role=role,
        kind="photo",
        storage_key=f"evidence/{world.project.id}/{uuid.uuid4()}.jpg",
        content_type="image/jpeg",
        size_bytes=10,
        file_sha256="a" * 64,
        captured_at=datetime(2026, 10, 14, 9, n, tzinfo=UTC),
        gps_time=datetime(2026, 10, 14, 9, n, tzinfo=UTC),
        latitude=6.4483,
        longitude=7.5139,
        accuracy_m=5,
        device_id="phone-1",
        signature="c2ln",
        status=status,
    )
    db_session.add(row)
    await db_session.flush()
    return row


async def test_accepted_for_milestone_counts_only_accepted_supervisor_evidence(
    db_session: AsyncSession, world: World
) -> None:
    good1 = await add_evidence(db_session, world, role="supervisor", status="accepted", n=1)
    good2 = await add_evidence(db_session, world, role="supervisor", status="accepted", n=2)
    await add_evidence(db_session, world, role="contractor", status="accepted")  # never counts
    await add_evidence(db_session, world, role="supervisor", status="pending_checks")
    await add_evidence(db_session, world, role="supervisor", status="flagged")
    await add_evidence(db_session, world, role="supervisor", status="rejected")
    await add_evidence(
        db_session, world, role="supervisor", status="accepted", milestone=world.other_milestone
    )

    found = await service.accepted_for_milestone(db_session, world.milestone.id)
    assert [e.id for e in found] == [good1.id, good2.id]


async def test_accepted_for_milestone_is_empty_with_no_evidence(
    db_session: AsyncSession, world: World
) -> None:
    assert await service.accepted_for_milestone(db_session, world.milestone.id) == []
    assert await service.accepted_for_milestone(db_session, uuid.uuid4()) == []
