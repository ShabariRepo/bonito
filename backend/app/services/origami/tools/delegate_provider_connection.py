"""delegate_provider_connection — punt to the provider-connect modal.

Origami can't safely receive cloud credentials (access keys, GCP service
account JSON, etc.) from the model's tool params — the values would land
in chat history, audit logs, and the orchestrator's prompt buffer. So
when the user needs to connect a provider, we hand off to the existing
secure connection modal.

This tool is is_write=False because it doesn't mutate state directly. It
returns a structured signal the frontend acts on: open the connection
modal for the requested provider type. The actual connection happens
through the normal /api/providers/connect flow (encrypted DB column +
Vault), not via Origami.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


SUPPORTED_PROVIDERS = ["aws", "azure", "gcp", "openai", "anthropic", "groq"]


@register_tool
class DelegateProviderConnectionTool(OrigamiTool):
    name = "delegate_provider_connection"
    description = (
        "Open the secure provider-connect modal for the user. Use this when "
        "the user wants to connect a new cloud provider (AWS Bedrock, Azure "
        "AI Foundry, GCP Vertex, OpenAI, Anthropic, Groq) — Origami never "
        "receives credentials directly because that would leak them into "
        "chat history. This tool returns a UI signal the frontend acts on to "
        "open the modal at the right step. After the user completes the "
        "modal, the new provider appears in their org state automatically."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "provider_type": {
                "type": "string",
                "enum": SUPPORTED_PROVIDERS,
                "description": "Which provider to connect: aws / azure / gcp / openai / anthropic / groq",
            },
            "reason": {
                "type": "string",
                "maxLength": 500,
                "description": "Optional one-liner about WHY we're suggesting this provider (model availability, region, etc.)",
            },
        },
        "required": ["provider_type"],
        "additionalProperties": False,
    }
    is_write = False  # ← deliberately not a write; doesn't go through plan card

    async def execute(
        self,
        *,
        org_id: uuid.UUID,
        user: User,
        params: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        provider_type = (params.get("provider_type") or "").lower().strip()
        if provider_type not in SUPPORTED_PROVIDERS:
            return {
                "success": False,
                "error": "unsupported_provider",
                "message": (
                    f"Unknown provider_type '{provider_type}'. Supported: "
                    + ", ".join(SUPPORTED_PROVIDERS)
                ),
            }

        return {
            "success": True,
            "ui_action": "open_provider_modal",
            "provider_type": provider_type,
            "reason": params.get("reason"),
            "next_step": (
                f"The frontend will open the {provider_type} connection modal. "
                "Tell the user you're handing them off and what they need ready "
                "(e.g. 'have your AWS access key and secret ready')."
            ),
        }
