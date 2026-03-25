"""
GCS File Storage for Knowledge Base uploads.

All user-uploaded KB documents are persisted in GCS with strict
tenant isolation:

    gs://bonito-kb-prod/{org_id}/{kb_id}/{file_id}_{filename}

The org_id is ALWAYS derived from the authenticated user's token,
never from user input. This prevents any cross-tenant data access.
"""

import logging
import os
import json
import uuid
from typing import Optional

from google.cloud import storage as gcs_storage
from google.oauth2 import service_account as gcp_sa

logger = logging.getLogger(__name__)

# Bucket name -- override via env var for staging/dev
BUCKET_NAME = os.getenv("BONITO_KB_BUCKET", "bonito-kb-prod")

# Service account JSON can come from:
#   1. BONITO_KB_SA_KEY env var (JSON string)
#   2. BONITO_KB_SA_KEY_PATH env var (path to JSON file)
#   3. Application Default Credentials (dev only)
_client: Optional[gcs_storage.Client] = None


def _get_client() -> gcs_storage.Client:
    """Lazy-init GCS client with service account credentials."""
    global _client
    if _client is not None:
        return _client

    sa_json_str = os.getenv("BONITO_KB_SA_KEY")
    sa_key_path = os.getenv("BONITO_KB_SA_KEY_PATH")

    if sa_json_str:
        info = json.loads(sa_json_str)
        creds = gcp_sa.Credentials.from_service_account_info(info)
        _client = gcs_storage.Client(credentials=creds, project=info.get("project_id"))
        logger.info("GCS client initialized from BONITO_KB_SA_KEY env var")
    elif sa_key_path:
        creds = gcp_sa.Credentials.from_service_account_file(sa_key_path)
        with open(sa_key_path) as f:
            info = json.load(f)
        _client = gcs_storage.Client(credentials=creds, project=info.get("project_id"))
        logger.info(f"GCS client initialized from key file {sa_key_path}")
    else:
        # Fall back to ADC (works locally with gcloud auth)
        _client = gcs_storage.Client()
        logger.info("GCS client initialized with Application Default Credentials")

    return _client


def _build_path(org_id: uuid.UUID, kb_id: uuid.UUID, file_id: uuid.UUID, filename: str) -> str:
    """
    Build the GCS object path.

    Format: {org_id}/{kb_id}/{file_id}_{filename}

    org_id is always the first path component, enforcing tenant isolation
    at the storage level.
    """
    # Sanitize filename (strip directory traversal, keep extension)
    safe_name = filename.replace("/", "_").replace("\\", "_").replace("..", "_")
    return f"{org_id}/{kb_id}/{file_id}_{safe_name}"


async def upload_file(
    org_id: uuid.UUID,
    kb_id: uuid.UUID,
    file_id: uuid.UUID,
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """
    Upload a file to GCS.

    Returns the full GCS path (gs://bucket/path).
    """
    import asyncio

    client = _get_client()
    bucket = client.bucket(BUCKET_NAME)
    path = _build_path(org_id, kb_id, file_id, filename)
    blob = bucket.blob(path)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: blob.upload_from_string(content, content_type=content_type),
    )

    gcs_uri = f"gs://{BUCKET_NAME}/{path}"
    logger.info(f"Uploaded {filename} ({len(content)} bytes) to {gcs_uri}")
    return gcs_uri


async def download_file(
    org_id: uuid.UUID,
    kb_id: uuid.UUID,
    file_id: uuid.UUID,
    filename: str,
) -> bytes:
    """
    Download a file from GCS.

    The org_id in the path ensures tenant isolation -- even if someone
    guesses a file_id, they can't access another org's files because
    the path won't match.
    """
    import asyncio

    client = _get_client()
    bucket = client.bucket(BUCKET_NAME)
    path = _build_path(org_id, kb_id, file_id, filename)
    blob = bucket.blob(path)

    loop = asyncio.get_event_loop()
    content = await loop.run_in_executor(None, blob.download_as_bytes)

    logger.info(f"Downloaded {path} ({len(content)} bytes)")
    return content


async def delete_file(
    org_id: uuid.UUID,
    kb_id: uuid.UUID,
    file_id: uuid.UUID,
    filename: str,
) -> bool:
    """Delete a file from GCS. Returns True if deleted, False if not found."""
    import asyncio

    client = _get_client()
    bucket = client.bucket(BUCKET_NAME)
    path = _build_path(org_id, kb_id, file_id, filename)
    blob = bucket.blob(path)

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, blob.delete)
        logger.info(f"Deleted {path} from GCS")
        return True
    except Exception as e:
        if "404" in str(e) or "Not Found" in str(e):
            logger.warning(f"File {path} not found in GCS (already deleted?)")
            return False
        raise


async def delete_kb_folder(org_id: uuid.UUID, kb_id: uuid.UUID) -> int:
    """
    Delete all files for a knowledge base.

    Returns the count of deleted objects.
    """
    import asyncio

    client = _get_client()
    bucket = client.bucket(BUCKET_NAME)
    prefix = f"{org_id}/{kb_id}/"

    loop = asyncio.get_event_loop()
    blobs = await loop.run_in_executor(
        None, lambda: list(bucket.list_blobs(prefix=prefix))
    )

    count = 0
    for blob in blobs:
        await loop.run_in_executor(None, blob.delete)
        count += 1

    logger.info(f"Deleted {count} files from GCS prefix {prefix}")
    return count


async def generate_signed_url(
    org_id: uuid.UUID,
    kb_id: uuid.UUID,
    file_id: uuid.UUID,
    filename: str,
    expiration_minutes: int = 15,
) -> str:
    """
    Generate a signed download URL (time-limited).

    Used for serving file downloads to the frontend without proxying
    through the backend.
    """
    import asyncio
    from datetime import timedelta

    client = _get_client()
    bucket = client.bucket(BUCKET_NAME)
    path = _build_path(org_id, kb_id, file_id, filename)
    blob = bucket.blob(path)

    loop = asyncio.get_event_loop()
    url = await loop.run_in_executor(
        None,
        lambda: blob.generate_signed_url(
            expiration=timedelta(minutes=expiration_minutes),
            method="GET",
        ),
    )

    return url
