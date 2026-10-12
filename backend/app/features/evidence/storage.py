"""S3-compatible object storage for evidence files (MinIO locally, S3/R2/B2 in staging).

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


def presign_read(storage_key: str, expires_in: int = READ_URL_TTL_S) -> str:
    """URL for viewing a stored file, valid for 15 minutes by default."""
    url: str = get_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": get_settings().storage_bucket, "Key": storage_key},
        ExpiresIn=expires_in,
    )
    return url
