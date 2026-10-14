import io
import uuid
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.features.evidence import media, storage
from app.features.evidence.tests.conftest import World, add_evidence, bearer, make_user, make_world


def jpeg_with_exif(orientation: int = 1, size: tuple[int, int] = (120, 80)) -> bytes:
    """A JPEG that carries the phone make, model, owner name and an orientation tag."""
    image = Image.new("RGB", size, (200, 30, 30))
    exif = Image.Exif()
    exif[0x010F] = "Acme Cameras"  # Make
    exif[0x0110] = "Model X"  # Model
    exif[0x013B] = "Grace Okafor"  # Artist: a person's name
    exif[0x0112] = orientation
    out = io.BytesIO()
    image.save(out, "JPEG", exif=exif)
    return out.getvalue()


@pytest.fixture
async def world(db_session: AsyncSession) -> World:
    return await make_world(db_session)


def url(world: World) -> str:
    return f"/api/v1/projects/{world.project.id}/evidence"


# strip_exif


def test_strip_exif_removes_every_tag() -> None:
    original = jpeg_with_exif()
    assert dict(Image.open(io.BytesIO(original)).getexif()), "the test photo should carry EXIF"
    stripped = media.strip_exif(original)
    assert dict(Image.open(io.BytesIO(stripped)).getexif()) == {}
    assert b"Acme Cameras" not in stripped and b"Grace Okafor" not in stripped


def test_strip_exif_applies_the_rotation_before_dropping_it() -> None:
    stripped = Image.open(io.BytesIO(media.strip_exif(jpeg_with_exif(orientation=6, size=(120, 80)))))
    assert stripped.size == (80, 120)  # rotated upright, and no orientation tag left to apply again


def test_strip_exif_refuses_a_file_that_is_not_an_image() -> None:
    with pytest.raises(ValueError):
        media.strip_exif(b"not an image")


# GET /projects/{id}/evidence


async def test_supervisor_sees_every_status_with_15_minute_urls(
    client: AsyncClient, db_session: AsyncSession, world: World, s3: Any
) -> None:
    for status in ("accepted", "flagged", "rejected", "pending_checks"):
        await add_evidence(db_session, world, status=status, s3=s3)
    response = await client.get(url(world), headers=bearer(world.supervisor))
    assert response.status_code == 200
    items = response.json()["items"]
    assert {i["status"] for i in items} == {"accepted", "flagged", "rejected", "pending_checks"}
    for item in items:
        assert item["is_client_copy"] is False
        assert item["read_url_expires_in"] == 900
        assert parse_qs(urlparse(item["read_url"]).query)["X-Amz-Expires"] == ["900"]
        assert item["storage_key"] in item["read_url"]  # the original file


async def test_client_sees_only_accepted_evidence_as_exif_free_copies(
    client: AsyncClient, db_session: AsyncSession, world: World, s3: Any
) -> None:
    original = jpeg_with_exif()
    accepted = await add_evidence(db_session, world, status="accepted", s3=s3, data=original)
    await add_evidence(db_session, world, status="flagged", s3=s3)
    await add_evidence(db_session, world, status="rejected", s3=s3)
    await add_evidence(db_session, world, status="pending_checks", s3=s3)

    response = await client.get(url(world), headers=bearer(world.client))
    assert response.status_code == 200
    items = response.json()["items"]
    assert [i["id"] for i in items] == [str(accepted.id)]
    item = items[0]
    assert item["is_client_copy"] is True
    assert "evidence-client/" in item["read_url"] and accepted.storage_key not in item["read_url"]

    copy = storage.read_object(media.client_copy_key(accepted.storage_key))
    assert copy is not None
    assert dict(Image.open(io.BytesIO(copy)).getexif()) == {}
    # The original is untouched, so supervisors and ops still see the full photo.
    assert dict(Image.open(io.BytesIO(storage.read_object(accepted.storage_key) or b"")).getexif())


async def test_the_client_copy_is_made_once_and_reused(
    client: AsyncClient, db_session: AsyncSession, world: World, s3: Any
) -> None:
    row = await add_evidence(db_session, world, s3=s3, data=jpeg_with_exif())
    await client.get(url(world), headers=bearer(world.client))
    key = media.client_copy_key(row.storage_key)
    first = s3.head_object(Bucket=get_settings().storage_bucket, Key=key)
    await client.get(url(world), headers=bearer(world.client))
    second = s3.head_object(Bucket=get_settings().storage_bucket, Key=key)
    assert first["ETag"] == second["ETag"]
    assert first["LastModified"] == second["LastModified"]


async def test_a_client_gets_the_original_video_link(
    client: AsyncClient, db_session: AsyncSession, world: World, s3: Any
) -> None:
    video = await add_evidence(db_session, world, kind="video", s3=s3)
    response = await client.get(url(world), headers=bearer(world.client))
    item = response.json()["items"][0]
    assert item["id"] == str(video.id)
    assert item["is_client_copy"] is False  # videos have no EXIF stripper yet
    assert video.storage_key in item["read_url"]


async def test_contractor_and_ops_see_every_status(
    client: AsyncClient, db_session: AsyncSession, world: World, s3: Any
) -> None:
    await add_evidence(db_session, world, status="flagged", s3=s3)
    for who in (world.contractor, world.ops):
        response = await client.get(url(world), headers=bearer(who))
        assert response.status_code == 200
        assert [i["status"] for i in response.json()["items"]] == ["flagged"]


async def test_filters(client: AsyncClient, db_session: AsyncSession, world: World, s3: Any) -> None:
    a = await add_evidence(db_session, world, status="accepted", s3=s3)
    b = await add_evidence(db_session, world, status="flagged", s3=s3, milestone=world.other_milestone)
    c = await add_evidence(db_session, world, status="accepted", role="contractor", s3=s3)
    d = await add_evidence(db_session, world, status="accepted", kind="video", s3=s3, no_milestone=True)
    headers = bearer(world.supervisor)

    async def ids(**params: Any) -> set[str]:
        response = await client.get(url(world), params=params, headers=headers)
        assert response.status_code == 200
        return {i["id"] for i in response.json()["items"]}

    assert await ids() == {str(a.id), str(b.id), str(c.id), str(d.id)}
    assert await ids(milestone_id=str(world.other_milestone.id)) == {str(b.id)}
    assert await ids(status="flagged") == {str(b.id)}
    assert await ids(kind="video") == {str(d.id)}
    assert await ids(captured_by_role="contractor") == {str(c.id)}
    assert await ids(status="accepted", captured_by_role="supervisor", kind="photo") == {str(a.id)}


async def test_invalid_filter_values_are_422(client: AsyncClient, world: World) -> None:
    response = await client.get(url(world), params={"status": "nonsense"}, headers=bearer(world.supervisor))
    assert response.status_code == 422


async def test_pages_with_a_cursor_never_repeat_or_skip(
    client: AsyncClient, db_session: AsyncSession, world: World, s3: Any
) -> None:
    made = {str((await add_evidence(db_session, world, s3=s3)).id) for _ in range(5)}
    headers = bearer(world.supervisor)
    seen: list[str] = []
    cursor: str | None = None
    for _ in range(5):
        params: dict[str, Any] = {"limit": 2}
        if cursor:
            params["cursor"] = cursor
        body = (await client.get(url(world), params=params, headers=headers)).json()
        seen += [i["id"] for i in body["items"]]
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert len(seen) == 5 and set(seen) == made


async def test_a_bad_cursor_is_422(client: AsyncClient, world: World) -> None:
    response = await client.get(url(world), params={"cursor": "nonsense"}, headers=bearer(world.supervisor))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_cursor"


async def test_someone_not_on_the_project_gets_403(
    client: AsyncClient, db_session: AsyncSession, world: World
) -> None:
    for role in ("client", "supervisor", "contractor"):
        stranger = await make_user(db_session, role)
        response = await client.get(url(world), headers=bearer(stranger))
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "not_project_member"


async def test_signed_out_is_401_and_unknown_project_is_404(client: AsyncClient, world: World) -> None:
    assert (await client.get(url(world))).status_code == 401
    response = await client.get(f"/api/v1/projects/{uuid.uuid4()}/evidence", headers=bearer(world.supervisor))
    assert response.status_code == 404


async def test_another_projects_evidence_is_not_listed(
    client: AsyncClient, db_session: AsyncSession, world: World, s3: Any
) -> None:
    other = await make_world(db_session)
    await add_evidence(db_session, other, s3=s3)
    response = await client.get(url(world), headers=bearer(world.supervisor))
    assert response.json()["items"] == []
