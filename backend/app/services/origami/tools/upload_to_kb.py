"""upload_to_kb — add inline documents to a knowledge base.

Phase 2 MVP shape: accepts a list of {title, content} pairs and creates
KBDocument rows with status='pending'. The existing ingestion pipeline
picks up pending docs, chunks them, and embeds them.

For file uploads (PDF, DOCX, etc.) the frontend handles the file picker
out-of-band — Origami can suggest the right KB and let the user upload
via the existing KB detail page. This tool is for the "paste this text"
flow.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


MAX_DOCS_PER_CALL = 20
MAX_DOC_CONTENT_LEN = 100_000  # 100KB per inline document


@register_tool
class UploadToKbTool(OrigamiTool):
    name = "upload_to_kb"
    description = (
        "Add inline text documents to an existing knowledge base. Use this "
        "when the user pastes content directly or wants to seed a KB with "
        "specific snippets (FAQs, policy text, sample answers, etc). Each "
        "document gets a title and a content body; the existing ingestion "
        "pipeline chunks and embeds them automatically. For PDF / DOCX / "
        "large file uploads, point the user at the KB detail page instead — "
        "this tool is for the paste-content path. Max 20 docs per call, "
        "100KB content limit each."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "kb_id": {"type": "string", "description": "UUID of the destination KB"},
            "documents": {
                "type": "array",
                "minItems": 1,
                "maxItems": MAX_DOCS_PER_CALL,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "minLength": 1, "maxLength": 500},
                        "content": {"type": "string", "minLength": 1, "maxLength": MAX_DOC_CONTENT_LEN},
                        "file_type": {
                            "type": "string",
                            "enum": ["txt", "md", "html"],
                            "description": "Hint about content format (default 'txt')",
                        },
                    },
                    "required": ["title", "content"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["kb_id", "documents"],
        "additionalProperties": False,
    }
    is_write = True

    async def execute(
        self,
        *,
        org_id: uuid.UUID,
        user: User,
        params: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        from app.models.knowledge_base import KnowledgeBase, KBDocument

        try:
            kb_id = uuid.UUID(str(params.get("kb_id")))
        except (TypeError, ValueError):
            return {"success": False, "error": "invalid_kb_id",
                    "message": "kb_id must be a valid UUID."}

        # Cross-tenant check: KB must belong to user's org
        kb_row = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == kb_id, KnowledgeBase.org_id == org_id
            )
        )
        kb = kb_row.scalar_one_or_none()
        if not kb:
            return {"success": False, "error": "kb_not_found",
                    "message": "Knowledge base not found in your organization."}

        docs = params.get("documents") or []
        if not docs or not isinstance(docs, list):
            return {"success": False, "error": "no_documents",
                    "message": "documents must be a non-empty list."}

        created_ids: list[str] = []
        skipped: list[dict[str, Any]] = []

        for doc in docs[:MAX_DOCS_PER_CALL]:
            if not isinstance(doc, dict):
                skipped.append({"reason": "not_an_object"})
                continue
            title = (doc.get("title") or "").strip()
            content = (doc.get("content") or "").strip()
            if not title or not content:
                skipped.append({"title": title or "(missing)", "reason": "missing_title_or_content"})
                continue
            if len(content) > MAX_DOC_CONTENT_LEN:
                skipped.append({"title": title, "reason": "content_too_large"})
                continue

            content_bytes = content.encode("utf-8")
            file_hash = hashlib.sha256(content_bytes).hexdigest()
            file_type = doc.get("file_type") or "txt"

            kbd = KBDocument(
                knowledge_base_id=kb.id,
                org_id=org_id,
                file_name=title[:500],
                file_path=None,
                file_type=file_type,
                file_size=len(content_bytes),
                file_hash=file_hash,
                status="pending",
                extra_metadata={
                    "source": "origami_inline_upload",
                    "user_id": str(user.id),
                    "raw_content": content,  # ingestion pipeline reads this for inline docs
                },
            )
            db.add(kbd)
            await db.flush()
            created_ids.append(str(kbd.id))

        await db.commit()

        return {
            "success": True,
            "kb_id": str(kb.id),
            "kb_name": kb.name,
            "documents_created": len(created_ids),
            "document_ids": created_ids,
            "skipped": skipped,
            "next_step": (
                "Docs are queued for chunking + embedding. Status will move "
                "from 'pending' → 'processing' → 'ready' as the ingestion "
                "pipeline runs."
            ),
        }
