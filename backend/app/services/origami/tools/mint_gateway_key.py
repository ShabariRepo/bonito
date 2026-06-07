"""mint_gateway_key — create a bn- gateway key for the customer.

This is the key the customer puts in their own application to call
Bonito's gateway. The raw key value is returned ONCE in the tool result
— frontend should display it prominently with a Copy button and a clear
"this won't be shown again" warning.

NOTE: org_id on the new GatewayKey is ALWAYS taken from auth context,
never from params. Sanitize_params strips org_id from the model's input
before execute() runs.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


@register_tool
class MintGatewayKeyTool(OrigamiTool):
    name = "mint_gateway_key"
    description = (
        "Mint a new bn- gateway key for the user's organization. They use this "
        "key in their own application to call Bonito's gateway (Authorization: "
        "Bearer bn-...). The raw value is returned ONCE in the response — the "
        "frontend will show it with a Copy button. Tell the user to store it "
        "securely; we can only show a hashed prefix afterward. Default rate "
        "limit is 60 req/min."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "minLength": 1,
                "maxLength": 255,
                "description": "Display name for the key, e.g. 'shopify-prod' or 'staging'",
            },
            "rate_limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10000,
                "description": "Per-minute rate limit (default 60)",
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
        from app.models.gateway import GatewayKey
        from app.services.feature_gate import feature_gate

        # Quota check — tiered cap on number of active (non-revoked) keys
        try:
            sub = await feature_gate.get_organization_subscription(db, str(org_id))
            tier = (sub["tier"].value if hasattr(sub["tier"], "value") else str(sub["tier"])).lower()
        except Exception:
            tier = "free"

        key_caps = {"free": 1, "builder": 3, "starter": 3, "growth": 10, "pro": 25}
        cap = key_caps.get(tier)
        if cap is not None:
            existing = await db.execute(
                select(func.count(GatewayKey.id)).where(
                    GatewayKey.org_id == org_id,
                    GatewayKey.revoked_at.is_(None),
                )
            )
            count = int(existing.scalar_one() or 0)
            if count >= cap:
                return {
                    "success": False,
                    "error": "key_quota_exceeded",
                    "message": f"You're at {count}/{cap} active gateway keys on the {tier} tier.",
                    "tier": tier,
                }

        name = (params.get("name") or "").strip()
        if not name:
            return {"success": False, "error": "missing_name", "message": "Key name is required."}

        rate_limit = int(params.get("rate_limit") or 60)
        if rate_limit < 1:
            rate_limit = 60

        raw = "bn-" + secrets.token_hex(32)
        key_hash = hashlib.sha256(raw.encode()).hexdigest()
        display_prefix = raw[:12] + "..."

        key = GatewayKey(
            org_id=org_id,                  # ← FROM SERVER, never from params
            key_hash=key_hash,
            key_prefix=display_prefix,
            name=name,
            rate_limit=rate_limit,
        )
        db.add(key)
        await db.flush()
        await db.commit()

        return {
            "success": True,
            "key_id": str(key.id),
            "key_prefix": key.key_prefix,
            "raw_key": raw,                 # ← shown ONCE; frontend must surface this
            "raw_key_warning": "This is the only time the full key will be displayed. Store it in your app's secret manager now.",
            "name": key.name,
            "rate_limit": key.rate_limit,
            "next_step": (
                "Use it in your app: `Authorization: Bearer " + raw + "`. "
                "Point your client at https://api.getbonito.com/v1/chat/completions "
                "(or http://localhost:8001 locally)."
            ),
        }
