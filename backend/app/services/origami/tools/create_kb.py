"""create_kb — first write tool for Origami.

State-mutating. Origami does NOT execute this directly when the model
calls it — the orchestrator detects is_write=True, buffers the call into
a PlanCard, and yields it to the user as a `plan_ready` event. Only on
explicit Deploy click does execute() actually run.

Creates an empty `upload` source-type knowledge base. Documents get added
via separate `upload_to_kb` calls in Phase 2.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


@register_tool
class CreateKbTool(OrigamiTool):
    name = "create_kb"
    description = (
        "Create a new knowledge base for the user's organization. The KB starts "
        "empty; documents are added in a follow-up step. Use this when the user "
        "wants to give an agent a corpus of documents to reference (support docs, "
        "product info, FAQs, etc.). Returns the new kb_id which can be passed "
        "to link_kb_to_agent later."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "minLength": 1,
                "maxLength": 255,
                "description": "Display name, e.g. 'shopify-support-docs'",
            },
            "description": {
                "type": "string",
                "maxLength": 2000,
                "description": "Optional summary of what's in this KB",
            },
            "embedding_model": {
                "type": "string",
                "description": "Embedding model id (default 'auto' lets Bonito pick)",
            },
        },
        "required": ["name"],
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
        from app.models.knowledge_base import KnowledgeBase
        from app.services.feature_gate import feature_gate

        # Pre-flight tier check — fail fast on quota violation
        try:
            subscription = await feature_gate.get_organization_subscription(db, str(org_id))
            tier_enum = subscription["tier"]
            tier_name = tier_enum.value if hasattr(tier_enum, "value") else str(tier_enum)
        except Exception:
            tier_name = "free"

        kb_caps = {"free": 0, "builder": 1, "starter": 2, "growth": 5, "pro": 20}
        cap = kb_caps.get(tier_name.lower(), None)
        if cap is not None:
            existing = await db.execute(
                select(func.count(KnowledgeBase.id)).where(KnowledgeBase.org_id == org_id)
            )
            existing_count = int(existing.scalar_one() or 0)
            if existing_count >= cap:
                return {
                    "success": False,
                    "error": "kb_quota_exceeded",
                    "message": (
                        f"You're at {existing_count}/{cap} KBs on the {tier_name} tier. "
                        f"Upgrade to add more."
                    ),
                    "tier": tier_name,
                    "current_count": existing_count,
                    "cap": cap,
                }

        name = (params.get("name") or "").strip()
        if not name:
            return {"success": False, "error": "missing_name", "message": "KB name is required."}

        kb = KnowledgeBase(
            org_id=org_id,
            name=name,
            description=params.get("description"),
            source_type="upload",
            source_config={},
            embedding_model=params.get("embedding_model") or "auto",
            status="pending",
        )
        db.add(kb)
        await db.flush()
        await db.commit()

        return {
            "success": True,
            "kb_id": str(kb.id),
            "name": kb.name,
            "status": kb.status,
            "embedding_model": kb.embedding_model,
            "next_step": "Upload documents via upload_to_kb, or link to an agent via link_kb_to_agent.",
        }
