"""bonito_knowledge — per-org "bonito-knowledge" KB seeding and retrieval.

The Origami orchestrator can manipulate platform state (create projects,
agents, KBs, gateway keys) but it cannot answer "how does Bonito work"
questions without a corpus to read from. This module provides the
seeding side (write platform docs + OpenAPI schema + CLI help into a
per-org `bonito-knowledge` KB) and the retrieval side (embed a query,
return top-K matching chunks for RAG injection into the system prompt).

Both sides reuse `kb_ingestion.EmbeddingGenerator` + `search_chunks`,
so we don't reinvent the embed/vector layer.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


BONITO_KNOWLEDGE_KB_NAME = "bonito-knowledge"
BONITO_KNOWLEDGE_DESCRIPTION = (
    "Platform reference corpus: Bonito docs, OpenAPI surface, and CLI "
    "help. Used by Origami to answer 'how does X work' questions."
)


async def get_or_create_bonito_knowledge_kb(
    db: AsyncSession,
    org_id: uuid.UUID,
):
    """Return the org's bonito-knowledge KB, creating it if missing.

    Idempotent. Safe to call on every Origami turn (it just SELECTs after
    the first call).
    """
    from app.models.knowledge_base import KnowledgeBase

    row = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.org_id == org_id,
            KnowledgeBase.name == BONITO_KNOWLEDGE_KB_NAME,
        )
    )
    kb = row.scalar_one_or_none()
    if kb:
        return kb

    kb = KnowledgeBase(
        org_id=org_id,
        name=BONITO_KNOWLEDGE_KB_NAME,
        description=BONITO_KNOWLEDGE_DESCRIPTION,
        source_type="manual",  # docs come from extractors, not a cloud bucket
        status="active",
    )
    db.add(kb)
    await db.flush()
    return kb


async def seed_for_org(
    db: AsyncSession,
    org_id: uuid.UUID,
    sources: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Run the ingestion extractors and write IngestionRecords into the
    org's bonito-knowledge KB as KBDocuments with status='pending'.

    The existing kb_ingestion pipeline picks up pending docs from there,
    chunks + embeds + writes vectors. Same path as inline `upload_to_kb`.

    Returns a summary dict with counts per source + total written.
    """
    from app.models.knowledge_base import KBDocument
    from app.services.origami.ingestion.unified_ingester import ingest_all, summarize

    kb = await get_or_create_bonito_knowledge_kb(db, org_id)

    records = ingest_all(sources=sources) if sources else ingest_all()
    summary = summarize(records)

    # Idempotency: skip records whose stable_id already exists for this KB.
    # The KBDocument.file_name column carries the stable_id so future re-runs
    # only insert new chunks.
    existing_rows = await db.execute(
        select(KBDocument.file_name).where(
            KBDocument.knowledge_base_id == kb.id,
            KBDocument.org_id == org_id,
        )
    )
    existing_ids = {r[0] for r in existing_rows.all()}

    written = 0
    for r in records:
        sid = r.stable_id()
        if sid in existing_ids:
            continue
        content_bytes = r.content.encode("utf-8")
        kbd = KBDocument(
            knowledge_base_id=kb.id,
            org_id=org_id,
            file_name=sid,
            file_path=None,
            file_type="md",
            file_size=len(content_bytes),
            file_hash=hashlib.sha256(content_bytes).hexdigest(),
            status="pending",
            extra_metadata={
                "source": "bonito-knowledge",
                "source_type": r.source_type.value if hasattr(r.source_type, "value") else str(r.source_type),
                "raw_content": r.content,
                "title": r.title,
                "metadata": r.metadata,
            },
        )
        db.add(kbd)
        written += 1

    await db.commit()
    return {
        "kb_id": str(kb.id),
        "kb_name": kb.name,
        "extracted": summary,
        "written": written,
        "skipped_existing": len(existing_ids),
    }


async def retrieve_context_for_query(
    db: AsyncSession,
    org_id: uuid.UUID,
    query: str,
    top_k: int = 3,
    min_score: float = 0.4,
) -> list[dict[str, Any]]:
    """Embed `query`, search the org's bonito-knowledge KB, return top-K chunks.

    Returns an empty list if the KB doesn't exist yet OR if no chunks match
    above min_score. The orchestrator should gracefully skip injection in
    those cases (a fresh org with no seed = no platform context, fall back
    to the system prompt alone).
    """
    from app.models.knowledge_base import KnowledgeBase
    from app.services.kb_ingestion import EmbeddingGenerator, search_chunks

    kb_row = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.org_id == org_id,
            KnowledgeBase.name == BONITO_KNOWLEDGE_KB_NAME,
        )
    )
    kb = kb_row.scalar_one_or_none()
    if not kb:
        return []

    try:
        gen = EmbeddingGenerator(org_id=org_id)
        embeddings = await gen.generate_embeddings(
            [query],
            dimensions=kb.embedding_dimensions if hasattr(kb, "embedding_dimensions") else None,
        )
    except Exception as e:
        logger.warning("bonito-knowledge query embedding failed: %s", e)
        return []

    if not embeddings or not embeddings[0]:
        return []

    try:
        chunks = await search_chunks(
            kb_id=kb.id,
            query_embedding=embeddings[0],
            top_k=top_k,
            min_score=min_score,
            org_id=org_id,
        )
    except Exception as e:
        logger.warning("bonito-knowledge vector search failed: %s", e)
        return []

    return chunks or []


def format_context_for_prompt(chunks: list[dict[str, Any]]) -> str:
    """Render retrieved chunks as a system-prompt context block.

    Returns an empty string if no chunks (so the orchestrator can
    concatenate unconditionally).
    """
    if not chunks:
        return ""
    parts = ["## Platform reference (retrieved from bonito-knowledge):"]
    for i, c in enumerate(chunks, start=1):
        text = c.get("content") or c.get("text") or ""
        if not text:
            continue
        parts.append(f"\n[{i}] {text.strip()}")
    parts.append(
        "\nUse the above as ground truth when the user asks about how "
        "Bonito works. Cite specific terms when relevant. If the question "
        "isn't covered above, say so plainly instead of guessing."
    )
    return "\n".join(parts)
