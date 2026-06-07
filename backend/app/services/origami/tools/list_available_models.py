"""list_available_models — what models the org can actually use right now.

Joins models → cloud_providers, filtered to the org's *active* providers.
Grouped by provider so Origami can suggest model choices that match the
user's connected infrastructure (don't recommend Sonnet via Bedrock if
they only have Vertex connected).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


@register_tool
class ListAvailableModelsTool(OrigamiTool):
    name = "list_available_models"
    description = (
        "Return the list of AI models the user's organization can actually "
        "use, grouped by the connected cloud provider. Only includes models "
        "from providers with status='active'. Use this BEFORE proposing a "
        "build so you only recommend models the user can actually run."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "provider_type": {
                "type": "string",
                "description": "Optional filter: only return models from this provider type (aws, azure, gcp, openai, anthropic, groq).",
            },
        },
        "required": [],
        "additionalProperties": False,
    }
    is_write = False

    async def execute(
        self,
        *,
        org_id: uuid.UUID,
        user: User,
        params: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        from app.models.cloud_provider import CloudProvider
        from app.models.model import Model

        provider_filter = params.get("provider_type")

        # Pull active providers + their models in one query
        stmt = (
            select(
                Model.id,
                Model.model_id,
                Model.display_name,
                Model.status,
                Model.capabilities,
                Model.pricing_info,
                CloudProvider.id.label("provider_id"),
                CloudProvider.provider_type,
                CloudProvider.status.label("provider_status"),
            )
            .join(CloudProvider, Model.provider_id == CloudProvider.id)
            .where(
                CloudProvider.org_id == org_id,
                CloudProvider.status == "active",
            )
        )
        if provider_filter:
            stmt = stmt.where(CloudProvider.provider_type == provider_filter)

        result = await db.execute(stmt)
        rows = list(result)

        # Group by provider
        by_provider: dict[str, dict[str, Any]] = {}
        for row in rows:
            provider_type = row.provider_type
            if provider_type not in by_provider:
                by_provider[provider_type] = {
                    "provider_id": str(row.provider_id),
                    "provider_type": provider_type,
                    "provider_status": row.provider_status,
                    "models": [],
                }
            by_provider[provider_type]["models"].append({
                "id": str(row.id),
                "model_id": row.model_id,
                "display_name": row.display_name,
                "status": row.status,
                "capabilities": row.capabilities or {},
                "pricing_info": row.pricing_info or {},
            })

        return {
            "providers": list(by_provider.values()),
            "summary": {
                "active_providers": len(by_provider),
                "total_models": sum(
                    len(p["models"]) for p in by_provider.values()
                ),
                "filter_applied": provider_filter,
            },
            "note": (
                "Only models from providers with status='active' are included. "
                "If you expected a model to appear but don't see it, the provider "
                "may be in pending or error status — use list_org_state to check."
            ),
        }
