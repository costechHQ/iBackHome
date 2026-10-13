from urllib.parse import parse_qs, urlparse

from app.features.evidence import storage


def test_presign_upload_url() -> None:
    url = storage.presign_upload("projects/p1/e1.jpg", "image/jpeg")
    parsed = urlparse(url)
    assert "/ibackhome-evidence/projects/p1/e1.jpg" in parsed.path
    assert parse_qs(parsed.query)["X-Amz-Expires"] == ["900"]


def test_presign_read_url_expires_in_15_minutes() -> None:
    query = parse_qs(urlparse(storage.presign_read("projects/p1/e1.jpg")).query)
    assert query["X-Amz-Expires"] == ["900"]
    assert "X-Amz-Signature" in query
