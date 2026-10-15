"""S3-compatible object storage for evidence files (SeaweedFS locally; S3/R2/B2 in staging and production).

Files are private: the app never exposes a public URL, only short-lived pre-signed ones.
"""

from functools import lru_cache
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings

UPLOAD_URL_TTL_S = 15 * 60
READ_URL_TTL_S = 15 * 60  # spec: read URLs expire after 15 minutes


@lru_cache
def get_client() -> Any:
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.storage_endpoint,
        aws_access_key_id=s.storage_access_key,
        aws_secret_access_key=s.storage_secret_key,
        region_name="us-east-1",  # MinIO ignores it; S3 clients insist on one
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ensure_bucket() -> None:
    """Create the evidence bucket if it does not exist yet (local/dev convenience)."""
    client, bucket = get_client(), get_settings().storage_bucket
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)


def presign_upload(storage_key: str, content_type: str, expires_in: int = UPLOAD_URL_TTL_S) -> str:
    """URL the device PUTs the file to. It must send the same Content-Type header."""
    url: str = get_client().generate_presigned_url(
        "put_object",
        Params={"Bucket": get_settings().storage_bucket, "Key": storage_key, "ContentType": content_type},
        ExpiresIn=expires_in,
    )
    return url


def head_object(storage_key: str) -> tuple[int, str] | None:
    """(size in bytes, content type) of a stored file, or None if it was never uploaded."""
    try:
        head = get_client().head_object(Bucket=get_settings().storage_bucket, Key=storage_key)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise
    return int(head["ContentLength"]), str(head.get("ContentType", ""))


def read_object(storage_key: str) -> bytes | None:
    """The stored file's bytes, or None if it is not there."""
    try:
        body = get_client().get_object(Bucket=get_settings().storage_bucket, Key=storage_key)["Body"]
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise
    data: bytes = body.read()
    return data


def delete_object(storage_key: str) -> None:
    get_client().delete_object(Bucket=get_settings().storage_bucket, Key=storage_key)


def presign_read(storage_key: str, expires_in: int = READ_URL_TTL_S) -> str:
    """URL for viewing a stored file, valid for 15 minutes by default."""
    url: str = get_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": get_settings().storage_bucket, "Key": storage_key},
        ExpiresIn=expires_in,
    )
    return url
