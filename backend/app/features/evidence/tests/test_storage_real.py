"""Upload through a presigned URL to the real object store (SeaweedFS in docker compose).

Skipped when no storage is listening, so it never blocks a machine or a CI run without it.
"""

import socket
import uuid
from urllib.parse import urlparse

import httpx
import pytest

from app.core.config import get_settings
from app.features.evidence import storage


def _storage_reachable() -> bool:
    endpoint = urlparse(get_settings().storage_endpoint)
    try:
        with socket.create_connection((endpoint.hostname or "127.0.0.1", endpoint.port or 9000), timeout=1):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(not _storage_reachable(), reason="object storage is not running")


def test_presigned_upload_and_read_against_real_storage() -> None:
    storage.get_client.cache_clear()
    storage.ensure_bucket()
    key = f"evidence/test/{uuid.uuid4()}.jpg"
    body = b"\xff\xd8\xff" + b"real storage test"
    try:
        put = httpx.put(
            storage.presign_upload(key, "image/jpeg"), content=body, headers={"Content-Type": "image/jpeg"}
        )
        assert put.status_code == 200
        assert storage.head_object(key) == (len(body), "image/jpeg")
        assert httpx.get(storage.presign_read(key)).content == body
    finally:
        storage.delete_object(key)
    assert storage.head_object(key) is None
