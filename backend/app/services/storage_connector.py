"""
Cloud Storage Connector for Knowledge Base

Connects to customer's S3/Azure Blob/GCS buckets using their provider credentials
(stored in Vault), lists and downloads files for KB ingestion.

Flow:
1. KB has source_type (s3/azure_blob/gcs) and source_config (bucket, prefix, etc.)
2. We find the matching provider for the org and pull creds from Vault
3. List objects in the bucket/prefix
4. Compare hashes to detect new/changed files
5. Download and feed into the existing ingestion pipeline
"""

import hashlib
import logging
import uuid
import asyncio
import json
import mimetypes
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from io import BytesIO

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.knowledge_base import KnowledgeBase, KBDocument, KBChunk
from app.models.cloud_provider import CloudProvider
from app.core.vault import vault_client
from app.core.database import get_db_session

logger = logging.getLogger(__name__)

# Supported file extensions for KB indexing
SUPPORTED_EXTENSIONS = {
    ".txt", ".md", ".pdf", ".docx", ".doc", ".html", ".htm",
    ".csv", ".json", ".xml", ".yaml", ".yml", ".rst", ".rtf",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB per file


class StorageConnector:
    """Base interface for cloud storage operations."""

    async def list_objects(self, bucket: str, prefix: str = "") -> List[Dict[str, Any]]:
        """List objects in a bucket/prefix. Returns list of {key, size, etag, last_modified}."""
        raise NotImplementedError

    async def download_object(self, bucket: str, key: str) -> bytes:
        """Download a single object from storage."""
        raise NotImplementedError


class S3Connector(StorageConnector):
    """AWS S3 storage connector."""

    def __init__(self, access_key_id: str, secret_access_key: str, region: str = "us-east-1"):
        import boto3
        self.client = boto3.client(
            "s3",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )

    async def list_objects(self, bucket: str, prefix: str = "") -> List[Dict[str, Any]]:
        objects = []
        paginator = self.client.get_paginator("list_objects_v2")
        params = {"Bucket": bucket}
        if prefix:
            params["Prefix"] = prefix

        loop = asyncio.get_event_loop()
        pages = await loop.run_in_executor(None, lambda: list(paginator.paginate(**params)))

        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                ext = "." + key.rsplit(".", 1)[-1].lower() if "." in key else ""
                if ext not in SUPPORTED_EXTENSIONS:
                    continue
                if obj["Size"] > MAX_FILE_SIZE:
                    logger.warning(f"Skipping {key}: too large ({obj['Size']} bytes)")
                    continue
                objects.append({
                    "key": key,
                    "size": obj["Size"],
                    "etag": obj.get("ETag", "").strip('"'),
                    "last_modified": obj.get("LastModified"),
                })
        return objects

    async def download_object(self, bucket: str, key: str) -> bytes:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(
            None, lambda: self.client.get_object(Bucket=bucket, Key=key)
        )
        return resp["Body"].read()


class AzureBlobConnector(StorageConnector):
    """Azure Blob Storage connector."""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str,
                 storage_account: str):
        from azure.identity import ClientSecretCredential
        from azure.storage.blob import BlobServiceClient

        credential = ClientSecretCredential(tenant_id, client_id, client_secret)
        account_url = f"https://{storage_account}.blob.core.windows.net"
        self.service = BlobServiceClient(account_url=account_url, credential=credential)

    async def list_objects(self, bucket: str, prefix: str = "") -> List[Dict[str, Any]]:
        container = self.service.get_container_client(bucket)
        objects = []
        loop = asyncio.get_event_loop()

        blobs = await loop.run_in_executor(
            None, lambda: list(container.list_blobs(name_starts_with=prefix or None))
        )
        for blob in blobs:
            ext = "." + blob.name.rsplit(".", 1)[-1].lower() if "." in blob.name else ""
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            if blob.size and blob.size > MAX_FILE_SIZE:
                continue
            objects.append({
                "key": blob.name,
                "size": blob.size,
                "etag": blob.etag.strip('"') if blob.etag else "",
                "last_modified": blob.last_modified,
            })
        return objects

    async def download_object(self, bucket: str, key: str) -> bytes:
        container = self.service.get_container_client(bucket)
        loop = asyncio.get_event_loop()
        blob_data = await loop.run_in_executor(
            None, lambda: container.download_blob(key).readall()
        )
        return blob_data


class GCSConnector(StorageConnector):
    """Google Cloud Storage connector."""

    def __init__(self, service_account_json: dict):
        from google.cloud import storage as gcs_storage
        from google.oauth2 import service_account as gcp_sa

        credentials = gcp_sa.Credentials.from_service_account_info(service_account_json)
        self.client = gcs_storage.Client(credentials=credentials, project=service_account_json.get("project_id"))

    async def list_objects(self, bucket: str, prefix: str = "") -> List[Dict[str, Any]]:
        gcs_bucket = self.client.bucket(bucket)
        loop = asyncio.get_event_loop()
        blobs = await loop.run_in_executor(
            None, lambda: list(gcs_bucket.list_blobs(prefix=prefix or None))
        )
        objects = []
        for blob in blobs:
            ext = "." + blob.name.rsplit(".", 1)[-1].lower() if "." in blob.name else ""
            if ext not in SUPPORTED_EXTENSIONS:
                continue
            if blob.size and blob.size > MAX_FILE_SIZE:
                continue
            objects.append({
                "key": blob.name,
                "size": blob.size,
                "etag": blob.etag or "",
                "last_modified": blob.updated,
            })
        return objects

    async def download_object(self, bucket: str, key: str) -> bytes:
        gcs_bucket = self.client.bucket(bucket)
        blob = gcs_bucket.blob(key)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, blob.download_as_bytes)


async def get_connector_for_kb(kb: KnowledgeBase, db: AsyncSession) -> Tuple[StorageConnector, str, str]:
    """
    Build the appropriate storage connector for a KB's source type,
    using the org's provider credentials from Vault.

    Returns (connector, bucket, prefix).
    """
    source_config = kb.source_config or {}
    provider_type_map = {
        "s3": "aws",
        "azure_blob": "azure",
        "gcs": "gcp",
    }
    provider_type = provider_type_map.get(kb.source_type)
    if not provider_type:
        raise ValueError(f"Unsupported source type: {kb.source_type}")

    # Find the org's active provider of the matching type
    result = await db.execute(
        select(CloudProvider).where(
            and_(
                CloudProvider.org_id == kb.org_id,
                CloudProvider.provider_type == provider_type,
                CloudProvider.status == "active",
            )
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise ValueError(f"No active {provider_type} provider found for org {kb.org_id}")

    # Pull credentials from Vault
    creds = await vault_client.get_secrets(f"providers/{provider.id}")
    if not creds:
        raise ValueError(f"No credentials found in Vault for provider {provider.id}")

    if kb.source_type == "s3":
        bucket = source_config.get("bucket", "")
        prefix = source_config.get("prefix", "")
        connector = S3Connector(
            access_key_id=creds.get("access_key_id", ""),
            secret_access_key=creds.get("secret_access_key", ""),
            region=creds.get("region", source_config.get("region", "us-east-1")),
        )
    elif kb.source_type == "azure_blob":
        bucket = source_config.get("container", "")
        prefix = source_config.get("prefix", "")
        connector = AzureBlobConnector(
            tenant_id=creds.get("tenant_id", ""),
            client_id=creds.get("client_id", ""),
            client_secret=creds.get("client_secret", ""),
            storage_account=source_config.get("storage_account", ""),
        )
    elif kb.source_type == "gcs":
        bucket = source_config.get("bucket", "")
        prefix = source_config.get("prefix", "")
        sa_json = creds.get("service_account_json")
        if isinstance(sa_json, str):
            sa_json = json.loads(sa_json)
        connector = GCSConnector(service_account_json=sa_json)
    else:
        raise ValueError(f"Unsupported source type: {kb.source_type}")

    if not bucket:
        raise ValueError(f"No bucket/container configured in source_config for KB {kb.id}")

    return connector, bucket, prefix


async def sync_kb_from_storage(kb_id: uuid.UUID) -> Dict[str, Any]:
    """
    Full sync: list objects in the configured bucket, compare with existing docs,
    download new/changed files, and feed into the ingestion pipeline.

    Returns sync summary with counts.
    """
    from app.services.kb_ingestion import process_document

    async with get_db_session() as db:
        result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
        kb = result.scalar_one_or_none()
        if not kb:
            raise ValueError(f"Knowledge base {kb_id} not found")

        if kb.source_type == "upload":
            raise ValueError("Cannot sync upload-based KB from storage")

        logger.info(f"Starting storage sync for KB {kb_id} ({kb.name}, {kb.source_type})")

        # Mark as syncing
        kb.status = "syncing"
        await db.commit()

        try:
            connector, bucket, prefix = await get_connector_for_kb(kb, db)

            # 1. List remote objects
            remote_objects = await connector.list_objects(bucket, prefix)
            logger.info(f"Found {len(remote_objects)} files in {kb.source_type}://{bucket}/{prefix}")

            # 2. Get existing documents (by file_path) to detect changes
            existing_result = await db.execute(
                select(KBDocument).where(KBDocument.knowledge_base_id == kb_id)
            )
            existing_docs = {doc.file_path: doc for doc in existing_result.scalars().all()}

            # 3. Determine new/changed/deleted
            new_files = []
            changed_files = []
            unchanged = 0
            remote_keys = set()

            for obj in remote_objects:
                key = obj["key"]
                remote_keys.add(key)
                etag = obj.get("etag", "")

                if key not in existing_docs:
                    new_files.append(obj)
                elif existing_docs[key].file_hash != etag:
                    changed_files.append(obj)
                else:
                    unchanged += 1

            # Files deleted from storage
            deleted_keys = set(existing_docs.keys()) - remote_keys
            deleted_count = 0
            for key in deleted_keys:
                doc = existing_docs[key]
                # Delete chunks first, then document
                await db.execute(
                    KBChunk.__table__.delete().where(KBChunk.document_id == doc.id)
                )
                await db.execute(
                    KBDocument.__table__.delete().where(KBDocument.id == doc.id)
                )
                kb.document_count = max(0, kb.document_count - 1)
                kb.chunk_count = max(0, kb.chunk_count - (doc.chunk_count or 0))
                deleted_count += 1
            if deleted_count:
                await db.commit()

            logger.info(
                f"Sync plan: {len(new_files)} new, {len(changed_files)} changed, "
                f"{unchanged} unchanged, {deleted_count} deleted"
            )

            # 4. Process new and changed files
            processed = 0
            errors = 0

            for obj_list, is_update in [(new_files, False), (changed_files, True)]:
                for obj in obj_list:
                    key = obj["key"]
                    filename = key.rsplit("/", 1)[-1] if "/" in key else key
                    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

                    try:
                        # Download file
                        content = await connector.download_object(bucket, key)
                        file_hash = obj.get("etag", hashlib.sha256(content).hexdigest())

                        if is_update:
                            # Delete old chunks for this document
                            old_doc = existing_docs[key]
                            await db.execute(
                                KBChunk.__table__.delete().where(KBChunk.document_id == old_doc.id)
                            )
                            kb.chunk_count = max(0, kb.chunk_count - (old_doc.chunk_count or 0))
                            kb.document_count = max(0, kb.document_count - 1)
                            # Update document record
                            old_doc.status = "pending"
                            old_doc.file_hash = file_hash
                            old_doc.file_size = len(content)
                            old_doc.chunk_count = 0
                            old_doc.error_message = None
                            old_doc.updated_at = datetime.now(timezone.utc)
                            await db.commit()
                            doc_id = old_doc.id
                        else:
                            # Create new document record
                            doc = KBDocument(
                                knowledge_base_id=kb_id,
                                org_id=kb.org_id,
                                file_name=filename,
                                file_path=key,
                                file_type=ext,
                                file_size=len(content),
                                file_hash=file_hash,
                                status="pending",
                            )
                            db.add(doc)
                            await db.flush()
                            await db.refresh(doc)
                            doc_id = doc.id
                            await db.commit()

                        # Process through ingestion pipeline (parse → chunk → embed → store)
                        await process_document(doc_id, content, kb_id)
                        processed += 1
                        logger.info(f"Processed {key} ({processed}/{len(new_files) + len(changed_files)})")

                        # Small delay between files to avoid embedding rate limits
                        await asyncio.sleep(1)

                    except Exception as e:
                        logger.error(f"Failed to process {key}: {e}")
                        errors += 1
                        # Mark doc as error if we created it
                        try:
                            if not is_update:
                                doc_result = await db.execute(
                                    select(KBDocument).where(KBDocument.id == doc_id)
                                )
                                doc_obj = doc_result.scalar_one_or_none()
                                if doc_obj:
                                    doc_obj.status = "error"
                                    doc_obj.error_message = str(e)[:1000]
                                    await db.commit()
                        except Exception:
                            pass

            # 5. Update KB status
            kb.status = "ready" if errors == 0 else ("error" if processed == 0 else "ready")
            kb.last_synced_at = datetime.now(timezone.utc)
            await db.commit()

            summary = {
                "new": len(new_files),
                "changed": len(changed_files),
                "unchanged": unchanged,
                "deleted": deleted_count,
                "processed": processed,
                "errors": errors,
                "total_remote": len(remote_objects),
            }
            logger.info(f"Sync complete for KB {kb_id}: {summary}")
            return summary

        except Exception as e:
            logger.error(f"Storage sync failed for KB {kb_id}: {e}")
            kb.status = "error"
            await db.commit()
            raise
