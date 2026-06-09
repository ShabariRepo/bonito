"""bonito_knowledge — PLATFORM-SHARED knowledge base for Origami.

Origami is the conversational builder for non-technical users. They need
to ask "how do I connect a provider", "what's a project token", "how do
I use the CLI" and get real answers. Those answers don't change between
customers — the same Bonito docs apply to every org.

So bonito-knowledge is a SINGLE platform-shared KB, not per-org. It
lives under a designated platform organization, gets seeded once, and is
read by Origami's orchestrator on every turn regardless of which
customer is chatting. The customer's own org_id still controls every
write (projects, agents, KBs they build) — only the platform reference
corpus is shared.

Implementation:
- A platform Organization is auto-created with a fixed UUID
  (PLATFORM_ORG_ID). The seeded KB lives there with source_type='platform'.
- retrieve_context_for_query bypasses the caller's org_id and reads the
  platform KB directly. Safe because the content is platform docs only,
  never customer data.
- seed_platform_knowledge() is idempotent; ops/cron can re-run on every
  docs update and only new chunks land.
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# Embedding model the gateway should route to. Bedrock Titan V2 is native
# 1024-dim (matches the KB column), is already what the rest of Bonito's
# KB pipeline uses by default, and works on any org that has AWS connected.
# Override via env if you prefer a different routable model.
PLATFORM_EMBED_MODEL = os.getenv(
    "ORIGAMI_EMBED_MODEL", "amazon.titan-embed-text-v2:0"
)


# Fixed UUID for the platform-shared organization that hosts bonito-knowledge.
# Picked as a recognizable-but-unlikely-to-collide value. Stored in the
# organizations table once, then reused forever.
PLATFORM_ORG_ID = uuid.UUID("00000000-0000-0000-0000-b04170900001")
PLATFORM_ORG_NAME = "_bonito_platform"

BONITO_KNOWLEDGE_KB_NAME = "bonito-knowledge"
BONITO_KNOWLEDGE_DESCRIPTION = (
    "Platform reference corpus: Bonito docs, OpenAPI surface, and CLI "
    "help. Shared across all orgs. Read by Origami on every turn so "
    "non-technical users can ask 'how does X work' and get real answers."
)
BONITO_KNOWLEDGE_SOURCE_TYPE = "platform"


async def _ensure_platform_org(db: AsyncSession):
    """Make sure the platform organization row exists. Returns the row."""
    from app.models.organization import Organization

    row = await db.execute(
        select(Organization).where(Organization.id == PLATFORM_ORG_ID)
    )
    org = row.scalar_one_or_none()
    if org:
        return org

    org = Organization(
        id=PLATFORM_ORG_ID,
        name=PLATFORM_ORG_NAME,
        subscription_tier="enterprise",  # so it has no quota limits
    )
    db.add(org)
    await db.flush()
    return org


async def get_or_create_platform_kb(db: AsyncSession):
    """Return the platform-shared bonito-knowledge KB, creating if missing.

    Idempotent. Safe to call on every Origami turn (just SELECTs after
    the first time).
    """
    from app.models.knowledge_base import KnowledgeBase

    row = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.name == BONITO_KNOWLEDGE_KB_NAME,
            KnowledgeBase.source_type == BONITO_KNOWLEDGE_SOURCE_TYPE,
        )
    )
    kb = row.scalar_one_or_none()
    if kb:
        return kb

    await _ensure_platform_org(db)

    kb = KnowledgeBase(
        org_id=PLATFORM_ORG_ID,
        name=BONITO_KNOWLEDGE_KB_NAME,
        description=BONITO_KNOWLEDGE_DESCRIPTION,
        source_type=BONITO_KNOWLEDGE_SOURCE_TYPE,
        status="active",
    )
    db.add(kb)
    await db.flush()
    await db.commit()
    return kb


async def seed_platform_knowledge(
    db: AsyncSession,
    sources: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Run the ingestion extractors and write IngestionRecords into the
    platform-shared bonito-knowledge KB.

    Each IngestionRecord is already pre-chunked by the extractor, so we
    write one KBDocument + one KBChunk per record. Embedding happens
    inline via the Bonito gateway (same path as retrieval), so no
    dependency on the platform org having a connected provider.

    Runs ONCE for the whole platform, not per-org. Idempotent — records
    whose stable_id already exists are skipped.

    Returns a summary dict with counts per source + total written + any
    embedding failures.
    """
    from app.models.knowledge_base import KBDocument, KBChunk
    from app.services.origami.ingestion.unified_ingester import ingest_all, summarize

    kb = await get_or_create_platform_kb(db)

    records = ingest_all(sources=sources) if sources else ingest_all()
    summary = summarize(records)

    existing_rows = await db.execute(
        select(KBDocument.file_name).where(
            KBDocument.knowledge_base_id == kb.id,
            KBDocument.org_id == PLATFORM_ORG_ID,
        )
    )
    existing_ids = {r[0] for r in existing_rows.all()}

    written = 0
    embed_failed = 0
    for r in records:
        sid = r.stable_id()
        if sid in existing_ids:
            continue

        # Embed inline via gateway
        vector = await _embed_via_gateway(r.content)
        if not vector:
            embed_failed += 1
            continue

        content_bytes = r.content.encode("utf-8")
        kbd = KBDocument(
            knowledge_base_id=kb.id,
            org_id=PLATFORM_ORG_ID,
            file_name=sid,
            file_path=None,
            file_type="md",
            file_size=len(content_bytes),
            file_hash=hashlib.sha256(content_bytes).hexdigest(),
            status="ready",  # Already embedded, skip the pending pipeline
            chunk_count=1,
            extra_metadata={
                "source": "bonito-knowledge",
                "source_type": r.source_type.value if hasattr(r.source_type, "value") else str(r.source_type),
                "raw_content": r.content,
                "title": r.title,
                "metadata": r.metadata,
            },
        )
        db.add(kbd)
        await db.flush()

        chunk = KBChunk(
            document_id=kbd.id,
            knowledge_base_id=kb.id,
            org_id=PLATFORM_ORG_ID,
            content=r.content,
            chunk_index=0,
            embedding=vector,
            source_file=sid,
            source_section=r.title,
            extra_metadata={
                "source_type": kbd.extra_metadata.get("source_type"),
                "title": r.title,
            },
        )
        db.add(chunk)
        written += 1

    await db.commit()
    return {
        "kb_id": str(kb.id),
        "kb_name": kb.name,
        "platform_org_id": str(PLATFORM_ORG_ID),
        "extracted": summary,
        "written": written,
        "skipped_existing": len(existing_ids),
        "embed_failed": embed_failed,
    }


async def _embed_via_gateway(text: str) -> Optional[list[float]]:
    """Generate a single embedding by calling Bonito's own gateway.

    Uses ORIGAMI_GATEWAY_KEY (the same bn- key Origami's chat path uses)
    against the gateway's /v1/embeddings endpoint. The gateway routes via
    LiteLLM to whatever provider the key's org has connected (Bedrock,
    GCP, Azure, OpenAI). No platform embedding key needed.

    Returns the embedding vector on success, None on any failure. Caller
    treats None as "fail open, skip RAG injection."
    """
    key = os.getenv("ORIGAMI_GATEWAY_KEY")
    if not key or not key.startswith("bn-"):
        logger.warning("ORIGAMI_GATEWAY_KEY missing or wrong prefix; skipping bonito-knowledge embed")
        return None

    # In-container default: backend listens on :8000 (host:8001 -> container:8000).
    # On host: hit the mapped port 8001. Override via BONITO_API_BASE_URL in prod.
    base = os.getenv("BONITO_API_BASE_URL", "http://localhost:8000").rstrip("/")
    url = f"{base}/v1/embeddings"

    # Retry with backoff on 429s — Bedrock Titan rate-limits aggressively
    # under bulk seeding. 4 attempts: 0s, 1s, 3s, 7s.
    import asyncio as _asyncio

    backoffs = [0, 1, 3, 7]
    for attempt, delay in enumerate(backoffs):
        if delay:
            await _asyncio.sleep(delay)
        try:
            async with httpx.AsyncClient(timeout=60.0) as http:
                r = await http.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": PLATFORM_EMBED_MODEL, "input": text},
                )
                if r.status_code == 429 and attempt < len(backoffs) - 1:
                    continue
                r.raise_for_status()
                data = r.json()
                return data["data"][0]["embedding"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < len(backoffs) - 1:
                continue
            logger.warning("bonito-knowledge gateway embedding failed: %s", e)
            return None
        except Exception as e:
            logger.warning("bonito-knowledge gateway embedding failed: %s", e)
            return None
    return None


async def retrieve_context_for_query(
    db: AsyncSession,
    query: str,
    top_k: int = 3,
    min_score: float = 0.4,
    # Backwards-compat: orchestrator used to pass org_id. Accept and ignore.
    org_id: Optional[uuid.UUID] = None,
) -> list[dict[str, Any]]:
    """Embed `query`, search the PLATFORM-shared bonito-knowledge KB,
    return top-K chunks.

    Cross-tenant by design: the platform KB is shared so all orgs see the
    same answers about how Bonito works. The caller's org_id is accepted
    for backwards-compat but unused — security is fine because the KB
    only contains public platform documentation, no customer data.

    Embeds via Bonito's own gateway (dogfood), not a separate platform
    API key.

    Returns empty list if the platform KB hasn't been seeded yet OR no
    chunks match above min_score. Orchestrator falls back to its baseline
    system prompt in that case.
    """
    from app.models.knowledge_base import KnowledgeBase
    from app.services.kb_ingestion import search_chunks

    kb_row = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.name == BONITO_KNOWLEDGE_KB_NAME,
            KnowledgeBase.source_type == BONITO_KNOWLEDGE_SOURCE_TYPE,
        )
    )
    kb = kb_row.scalar_one_or_none()
    if not kb:
        return []

    vector = await _embed_via_gateway(query)
    if not vector:
        return []

    try:
        # Use the platform org_id to satisfy search_chunks' ownership check.
        # The KB belongs to the platform org by design.
        chunks = await search_chunks(
            kb_id=kb.id,
            query_embedding=vector,
            top_k=top_k,
            min_score=min_score,
            org_id=PLATFORM_ORG_ID,
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
    parts = ["## Bonito platform reference (use as ground truth when explaining how the product works):"]
    for i, c in enumerate(chunks, start=1):
        text = c.get("content") or c.get("text") or ""
        if not text:
            continue
        parts.append(f"\n[{i}] {text.strip()}")
    parts.append(
        "\nWhen the user asks how Bonito works (providers, CLI, agents, "
        "KBs, tokens, billing, etc.) use the snippets above. If the "
        "question isn't covered, say so plainly instead of guessing. "
        "Always tailor the answer to a non-technical reader unless they "
        "ask for technical detail."
    )
    return "\n".join(parts)


# ── Backwards-compat aliases (orchestrator + script still call old names) ─

async def seed_for_org(
    db: AsyncSession,
    org_id: uuid.UUID,
    sources: Optional[list[str]] = None,
) -> dict[str, Any]:
    """DEPRECATED: alias to seed_platform_knowledge.

    The KB is now platform-shared, so the org_id parameter is ignored.
    Kept so existing scripts don't break. Prefer
    seed_platform_knowledge() in new code.
    """
    logger.info(
        "seed_for_org called with org_id=%s — routing to platform-shared KB. "
        "org_id is ignored.",
        org_id,
    )
    return await seed_platform_knowledge(db, sources=sources)


async def get_or_create_bonito_knowledge_kb(
    db: AsyncSession,
    org_id: Optional[uuid.UUID] = None,
):
    """DEPRECATED: alias to get_or_create_platform_kb. org_id ignored."""
    return await get_or_create_platform_kb(db)
