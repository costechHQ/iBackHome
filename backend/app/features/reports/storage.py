"""Where report PDFs are kept: the same S3-compatible store as evidence. Owner: James.

Uses the shared storage settings from core/config.py. Evidence has its own copy of this client
(features/evidence/storage.py, Abigail's); the rules say not to import another feature's modules,
so this small duplicate stays until storage moves to core/ (proposed in the Day 5 PR).
Files are private; readers get 15-minute pre-signed links only.
"""

from functools import lru_cache
from typing import Any

import boto3
from botocore.client import Config

from app.core.config import get_settings

READ_URL_TTL_S = 15 * 60


@lru_cache
def _client() -> Any:
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.storage_endpoint,
        aws_access_key_id=s.storage_access_key,
        aws_secret_access_key=s.storage_secret_key,
        region_name="us-east-1",  # S3-compatible stores ignore it; boto3 insists on one
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def pdf_key(project_id: object, week_start: object) -> str:
    return f"reports/{project_id}/{week_start}.pdf"


def put_pdf(key: str, data: bytes) -> None:
    """Upload a PDF (blocking: call it with asyncio.to_thread from async code)."""
    _client().put_object(
        Bucket=get_settings().storage_bucket, Key=key, Body=data, ContentType="application/pdf"
    )


def presign_read(key: str) -> str:
    url: str = _client().generate_presigned_url(
        "get_object", Params={"Bucket": get_settings().storage_bucket, "Key": key}, ExpiresIn=READ_URL_TTL_S
    )
    return url
