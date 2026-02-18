"""
Knowledge Base API routes — RAG document management and search.

All endpoints require JWT authentication (dashboard users).
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from fastapi.responses import JSONResponse
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase, KBDocument, KBChunk
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KBDocumentResponse,
    KBChunkResponse,
    KBSearchRequest,
    KBSearchResponse,
    KBSyncRequest,
    KBSyncStatus,
    KBUploadResponse,
    KBStats,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["knowledge-base"], prefix="/knowledge-bases")


# ─── Knowledge Base CRUD ───

@router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    body: KnowledgeBaseCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new knowledge base."""
    # Check for duplicate name within the organization
    result = await db.execute(
        select(KnowledgeBase).where(
            and_(KnowledgeBase.org_id == user.org_id, KnowledgeBase.name == body.name)
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Knowledge base '{body.name}' already exists"
        )

    # Validate source configuration based on source type
    if body.source_type in ["s3", "azure_blob", "gcs"]:
        if not body.source_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"source_config is required for {body.source_type}"
            )
        # Add source-specific validation here if needed

    kb = KnowledgeBase(
        org_id=user.org_id,
        name=body.name,
        description=body.description,
        source_type=body.source_type,
        source_config=body.source_config,
        embedding_model=body.embedding_model,
        embedding_dimensions=body.embedding_dimensions,
        chunk_size=body.chunk_size,
        chunk_overlap=body.chunk_overlap,
        sync_schedule=body.sync_schedule,
    )
    
    db.add(kb)
    await db.flush()
    await db.refresh(kb)
    
    logger.info(f"Created knowledge base {kb.id} ({kb.name}) for org {user.org_id}")
    return kb


@router.get("", response_model=List[KnowledgeBaseResponse])
async def list_knowledge_bases(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all knowledge bases for the organization."""
    result = await db.execute(
        select(KnowledgeBase)
        .where(KnowledgeBase.org_id == user.org_id)
        .order_by(desc(KnowledgeBase.created_at))
    )
    return list(result.scalars().all())


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific knowledge base by ID."""
    result = await db.execute(
        select(KnowledgeBase).where(
            and_(KnowledgeBase.id == kb_id, KnowledgeBase.org_id == user.org_id)
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    
    return kb


@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: uuid.UUID,
    body: KnowledgeBaseUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a knowledge base."""
    result = await db.execute(
        select(KnowledgeBase).where(
            and_(KnowledgeBase.id == kb_id, KnowledgeBase.org_id == user.org_id)
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    # Check for name conflicts if name is being changed
    if body.name and body.name != kb.name:
        result = await db.execute(
            select(KnowledgeBase).where(
                and_(
                    KnowledgeBase.org_id == user.org_id,
                    KnowledgeBase.name == body.name,
                    KnowledgeBase.id != kb_id
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Knowledge base '{body.name}' already exists"
            )

    # Update provided fields
    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(kb, field, value)
    
    kb.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(kb)
    
    logger.info(f"Updated knowledge base {kb.id} ({kb.name}) for org {user.org_id}")
    return kb


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a knowledge base and all its documents and chunks."""
    result = await db.execute(
        select(KnowledgeBase).where(
            and_(KnowledgeBase.id == kb_id, KnowledgeBase.org_id == user.org_id)
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    kb_name = kb.name
    await db.delete(kb)
    await db.flush()
    
    logger.info(f"Deleted knowledge base {kb_id} ({kb_name}) for org {user.org_id}")


# ─── Document Management ───

@router.get("/{kb_id}/documents", response_model=List[KBDocumentResponse])
async def list_documents(
    kb_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all documents in a knowledge base."""
    # Verify KB exists and belongs to user's org
    kb_result = await db.execute(
        select(KnowledgeBase).where(
            and_(KnowledgeBase.id == kb_id, KnowledgeBase.org_id == user.org_id)
        )
    )
    kb = kb_result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    result = await db.execute(
        select(KBDocument)
        .where(KBDocument.knowledge_base_id == kb_id)
        .order_by(desc(KBDocument.created_at))
    )
    return list(result.scalars().all())


@router.get("/{kb_id}/documents/{doc_id}", response_model=KBDocumentResponse)
async def get_document(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific document by ID."""
    # Verify KB exists and belongs to user's org
    kb_result = await db.execute(
        select(KnowledgeBase).where(
            and_(KnowledgeBase.id == kb_id, KnowledgeBase.org_id == user.org_id)
        )
    )
    kb = kb_result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    result = await db.execute(
        select(KBDocument).where(
            and_(KBDocument.id == doc_id, KBDocument.knowledge_base_id == kb_id)
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    
    return doc


@router.post("/{kb_id}/documents", response_model=KBUploadResponse)
async def upload_document(
    kb_id: uuid.UUID,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document to a knowledge base."""
    # Verify KB exists and belongs to user's org
    kb_result = await db.execute(
        select(KnowledgeBase).where(
            and_(KnowledgeBase.id == kb_id, KnowledgeBase.org_id == user.org_id)
        )
    )
    kb = kb_result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    if kb.source_type != "upload":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This knowledge base is configured for cloud storage, not direct uploads"
        )

    # Validate file type
    allowed_types = {".pdf", ".docx", ".txt", ".md", ".html", ".csv", ".json"}
    file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_types)}"
        )

    # Size limit: 50MB
    max_size = 50 * 1024 * 1024  # 50MB
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 50MB limit"
        )

    # Calculate file hash for deduplication
    import hashlib
    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate file
    result = await db.execute(
        select(KBDocument).where(
            and_(
                KBDocument.knowledge_base_id == kb_id,
                KBDocument.file_hash == file_hash
            )
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return KBUploadResponse(
            document_id=existing.id,
            file_name=existing.file_name,
            file_size=existing.file_size or 0,
            status=existing.status,
            message="File already exists (duplicate hash)"
        )

    # Create document record
    doc = KBDocument(
        knowledge_base_id=kb_id,
        org_id=user.org_id,
        file_name=file.filename,
        file_type=file_ext.lstrip("."),
        file_size=len(content),
        file_hash=file_hash,
        status="pending",
        extra_metadata={"uploaded_by": str(user.id), "upload_timestamp": datetime.now(timezone.utc).isoformat()}
    )

    db.add(doc)
    await db.flush()
    await db.refresh(doc)

    # Schedule background processing using the real ingestion pipeline
    from app.services.kb_ingestion import process_document
    background_tasks.add_task(process_document, doc.id, content, kb_id)

    logger.info(f"Uploaded document {doc.id} ({file.filename}) to KB {kb_id}")
    
    return KBUploadResponse(
        document_id=doc.id,
        file_name=file.filename,
        file_size=len(content),
        status="pending",
        message="File uploaded successfully, processing started"
    )


@router.delete("/{kb_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and all its chunks."""
    # Verify KB exists and belongs to user's org
    kb_result = await db.execute(
        select(KnowledgeBase).where(
            and_(KnowledgeBase.id == kb_id, KnowledgeBase.org_id == user.org_id)
        )
    )
    kb = kb_result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    result = await db.execute(
        select(KBDocument).where(
            and_(KBDocument.id == doc_id, KBDocument.knowledge_base_id == kb_id)
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    doc_name = doc.file_name
    chunk_count = doc.chunk_count
    
    await db.delete(doc)
    await db.flush()
    
    # Update KB counters
    kb.document_count = max(0, kb.document_count - 1)
    kb.chunk_count = max(0, kb.chunk_count - chunk_count)
    await db.flush()
    
    logger.info(f"Deleted document {doc_id} ({doc_name}) from KB {kb_id}")


# ─── Sync Operations ───

@router.post("/{kb_id}/sync", response_model=KBSyncStatus)
async def sync_knowledge_base(
    kb_id: uuid.UUID,
    body: KBSyncRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger sync from cloud storage."""
    # Verify KB exists and belongs to user's org
    result = await db.execute(
        select(KnowledgeBase).where(
            and_(KnowledgeBase.id == kb_id, KnowledgeBase.org_id == user.org_id)
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    if kb.source_type == "upload":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot sync upload-based knowledge base. Use document upload instead."
        )

    if kb.status == "syncing" and not body.force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sync already in progress. Use force=true to restart."
        )

    # Mark as syncing
    kb.status = "syncing"
    await db.flush()

    # Schedule background sync task
    background_tasks.add_task(_sync_from_cloud_storage, kb_id)

    logger.info(f"Started sync for KB {kb_id} ({kb.name})")
    
    return KBSyncStatus(
        knowledge_base_id=kb_id,
        status="syncing",
        progress_percentage=0,
        files_processed=0,
        files_total=0,
        started_at=datetime.now(timezone.utc)
    )


@router.get("/{kb_id}/sync-status", response_model=KBSyncStatus)
async def get_sync_status(
    kb_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current sync status for a knowledge base."""
    result = await db.execute(
        select(KnowledgeBase).where(
            and_(KnowledgeBase.id == kb_id, KnowledgeBase.org_id == user.org_id)
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    # For now, return basic status from the KB record
    # In a production system, this would check a separate sync_jobs table
    return KBSyncStatus(
        knowledge_base_id=kb_id,
        status=kb.status,
        progress_percentage=100 if kb.status == "ready" else None,
        files_processed=kb.document_count,
        files_total=kb.document_count,
        current_file=None
    )


# ─── Search Operations ───

@router.post("/{kb_id}/search", response_model=KBSearchResponse)
async def search_knowledge_base(
    kb_id: uuid.UUID,
    body: KBSearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search for relevant chunks in a knowledge base."""
    import time
    start_time = time.time()

    # Verify KB exists and belongs to user's org
    result = await db.execute(
        select(KnowledgeBase).where(
            and_(KnowledgeBase.id == kb_id, KnowledgeBase.org_id == user.org_id)
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    if kb.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Knowledge base is not ready (status: {kb.status})"
        )

    top_k = body.top_k if hasattr(body, "top_k") and body.top_k else 5
    
    # Generate embedding for the query
    from app.services.kb_ingestion import EmbeddingGenerator
    embedding_gen = EmbeddingGenerator(user.org_id)
    
    try:
        query_embeddings = await embedding_gen.generate_embeddings([body.query])
        if not query_embeddings:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")
        query_embedding = query_embeddings[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")
    
    # Vector similarity search using pgvector
    from sqlalchemy import text as sa_text
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    
    try:
        search_result = await db.execute(
            sa_text("""
                SELECT c.id, c.content, c.token_count, c.chunk_index,
                       c.source_file, c.source_page, c.source_section,
                       1 - (c.embedding <=> :query_vec::vector) AS relevance_score
                FROM kb_chunks c
                WHERE c.knowledge_base_id = :kb_id
                  AND c.org_id = :org_id
                  AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> :query_vec::vector
                LIMIT :top_k
            """),
            {
                "query_vec": embedding_str,
                "kb_id": str(kb_id),
                "org_id": str(user.org_id),
                "top_k": top_k,
            },
        )
        rows = search_result.fetchall()
    except Exception as e:
        logger.error(f"pgvector search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Vector search failed: {str(e)}")
    
    search_time_ms = int((time.time() - start_time) * 1000)
    
    results = []
    for row in rows:
        results.append({
            "chunk_id": str(row.id),
            "content": row.content,
            "source_file": row.source_file,
            "source_page": row.source_page,
            "source_section": row.source_section,
            "relevance_score": round(float(row.relevance_score), 4) if row.relevance_score else 0,
            "token_count": row.token_count,
        })
    
    return KBSearchResponse(
        query=body.query,
        results=results,
        total_results=len(results),
        search_time_ms=search_time_ms,
    )


# ─── Statistics ───

@router.get("/{kb_id}/stats", response_model=KBStats)
async def get_knowledge_base_stats(
    kb_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get statistics for a knowledge base."""
    # Verify KB exists and belongs to user's org
    result = await db.execute(
        select(KnowledgeBase).where(
            and_(KnowledgeBase.id == kb_id, KnowledgeBase.org_id == user.org_id)
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    # Get document type breakdown
    doc_types_result = await db.execute(
        select(KBDocument.file_type, func.count(KBDocument.id))
        .where(KBDocument.knowledge_base_id == kb_id)
        .group_by(KBDocument.file_type)
    )
    document_types = {row[0] or "unknown": row[1] for row in doc_types_result.fetchall()}

    # Get status breakdown
    status_result = await db.execute(
        select(KBDocument.status, func.count(KBDocument.id))
        .where(KBDocument.knowledge_base_id == kb_id)
        .group_by(KBDocument.status)
    )
    status_counts = {row[0]: row[1] for row in status_result.fetchall()}

    # Calculate average chunk size
    avg_chunk_size = 0.0
    if kb.chunk_count > 0:
        chunk_size_result = await db.execute(
            select(func.avg(KBChunk.token_count))
            .where(and_(KBChunk.knowledge_base_id == kb_id, KBChunk.token_count.isnot(None)))
        )
        avg_chunk_size = chunk_size_result.scalar() or 0.0

    return KBStats(
        total_documents=kb.document_count,
        total_chunks=kb.chunk_count,
        total_tokens=kb.total_tokens,
        document_types=document_types,
        status_counts=status_counts,
        avg_chunk_size=avg_chunk_size,
        last_sync=kb.last_synced_at
    )


# ─── Background Tasks (Placeholder implementations) ───

async def _process_uploaded_document(doc_id: uuid.UUID, content: bytes, kb_id: uuid.UUID):
    """Process an uploaded document in the background."""
    # TODO: Implement document processing pipeline
    # 1. Parse document content based on file type
    # 2. Split into chunks
    # 3. Generate embeddings
    # 4. Store chunks in database
    logger.info(f"Starting background processing for document {doc_id}")
    
    # Placeholder: just mark as processed for now
    from app.core.database import get_db_session
    async with get_db_session() as db:
        result = await db.execute(select(KBDocument).where(KBDocument.id == doc_id))
        doc = result.scalar_one_or_none()
        if doc:
            doc.status = "ready"  # In real implementation, this would be "processing" then "ready"
            await db.commit()


async def _sync_from_cloud_storage(kb_id: uuid.UUID):
    """Sync documents from cloud storage in the background."""
    # TODO: Implement cloud storage sync
    # 1. Connect to S3/Blob/GCS using credentials from source_config
    # 2. List files in the configured bucket/container
    # 3. Download and process new/changed files
    # 4. Update document records and process into chunks
    logger.info(f"Starting background sync for KB {kb_id}")
    
    # Placeholder: just mark as ready for now
    from app.core.database import get_db_session
    async with get_db_session() as db:
        result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
        kb = result.scalar_one_or_none()
        if kb:
            kb.status = "ready"
            kb.last_synced_at = datetime.now(timezone.utc)
            await db.commit()