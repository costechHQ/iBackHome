"""Fixtures for the evidence tests: an in-memory S3, a project with its people, and a job queue spy."""

import hashlib
import secrets
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import boto3
import pytest
from moto import mock_aws
from sqlalchemy.ext.asyncio import AsyncSession

from app.base.users import service as users
from app.base.users.models import User
from app.core.config import get_settings
from app.features.evidence import service, storage
from app.features.milestones import service as milestones
from app.features.milestones.models import Milestone
from app.features.milestones.schemas import MilestoneGroup
from app.features.projects import service as projects
from app.features.projects.models import Project, ProjectStatus
from app.features.projects.schemas import ProjectCreate
from app.features.projects.transitions import ActorRole


@pytest.fixture
def s3(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """An in-memory S3 with the evidence bucket, so upload tests run the same everywhere (CI too)."""
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.setenv(name, "test")
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=get_settings().storage_bucket)
        monkeypatch.setattr(storage, "get_client", lambda: client)
        yield client


@pytest.fixture
def queued(monkeypatch: pytest.MonkeyPatch) -> list[uuid.UUID]:
    """Records which evidence ids were queued for run_checks, without needing Redis."""
    ids: list[uuid.UUID] = []
    monkeypatch.setattr(service, "enqueue_run_checks", ids.append)
    return ids


async def make_user(session: AsyncSession, role: str) -> User:
    user = User(phone=f"+234803{secrets.randbelow(10**7):07d}", role=role, status="active")
    session.add(user)
    await session.flush()
    return user


def bearer(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {users.create_access_token(user)}"}


@dataclass
class World:
    """An active project with its client, contractor and assigned supervisor, plus two milestones."""

    client: User
    contractor: User
    supervisor: User
    ops: User
    project: Project
    milestone: Milestone
    other_milestone: Milestone


async def make_world(session: AsyncSession, *, active: bool = True) -> World:
    client = await make_user(session, "client")
    contractor = await make_user(session, "contractor")
    supervisor = await make_user(session, "supervisor")
    ops = await make_user(session, "ops")
    project = await projects.create_project(
        session,
        client,
        ProjectCreate(
            title="Duplex",
            address="12 Chime Avenue, Enugu",
            currency="NGN",
            budget_minor=45_000_000_00,
            contractor_phone=contractor.phone,
        ),
    )
    project.supervisor_id = supervisor.id
    await session.flush()
    first, second = await milestones.create_for_project(
        session,
        project.id,
        [
            MilestoneGroup(name="Foundation", amount_minor=10_000_000_00),
            MilestoneGroup(name="Roof", amount_minor=5_000_00),
        ],
        "NGN",
    )
    if active:
        await projects.transition(
            session, project.id, ProjectStatus.BOQ_REVIEW, ActorRole.CONTRACTOR, contractor.id
        )
        await projects.transition(session, project.id, ProjectStatus.ACTIVE, ActorRole.SYSTEM)
    return World(client, contractor, supervisor, ops, project, first, second)


def upload(s3: Any, key: str, *, size: int = 2048, content_type: str = "image/jpeg") -> bytes:
    body = secrets.token_bytes(size)
    s3.put_object(Bucket=get_settings().storage_bucket, Key=key, Body=body, ContentType=content_type)
    return body


def evidence_body(world: World, key: str, body: bytes, **overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "project_id": str(world.project.id),
        "milestone_id": str(world.milestone.id),
        "kind": "photo",
        "storage_key": key,
        "file_sha256": hashlib.sha256(body).hexdigest(),
        "captured_at": datetime(2026, 10, 14, 9, 30, 15, 123000, tzinfo=UTC).isoformat(),
        "latitude": 6.4483,
        "longitude": 7.5139,
        "accuracy_m": 8.5,
        "device_id": "phone-1",
        "signature": "c2lnbmF0dXJl",
    }
    return data | overrides
