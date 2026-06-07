"""check_tier_access — what's allowed at the user's subscription tier.

Returns the live tier matrix from feature_gate.py: current tier name,
hard limits, feature allow/deny grid, and a list of the next-tier features
they'd unlock by upgrading. Origami uses this to decide whether to propose
a build or surface an upgrade prompt.
"""

from __future__ import annotations

import math
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.origami.tools.base import OrigamiTool, register_tool


# Friendly names for features the model can reference in plain English
FEATURE_DESCRIPTIONS = {
    "models": "Access to model registry and playground",
    "playground": "Multi-model side-by-side playground",
    "routing": "Multi-provider routing + failover",
    "ai_context": "Knowledge bases (RAG)",
    "analytics": "Cost and usage analytics dashboard",
    "cli": "bonito-cli access for IaC + scripting",
    "audit": "Audit trail with export",
    "notifications": "Webhook / email / Slack notifications",
    "budget_alerts": "Spend caps and alerts",
    "vectorboost": "KB compression (3.9x-8x storage reduction)",
    "agent_hpa": "Agent autoscaling (horizontal pod autoscaler)",
    "sso": "SSO / SAML (Okta, Azure AD, Google Workspace)",
    "rbac": "Role-based access control",
    "iac_templates": "Terraform / IaC templates",
    "compliance": "SOC-2 / HIPAA / GDPR compliance checks",
    "on_premise": "On-premise / self-hosted deployment",
    "custom_integrations": "Custom integrations and webhooks",
    "dedicated_support": "Dedicated support engineer",
    "bonbon_agents": "BonBon (simplified) agents",
}

TIER_ORDER = ["free", "starter", "pro", "enterprise"]


def _serialize_limit(v: Any) -> Any:
    """Convert math.inf to the string 'unlimited' so it survives JSON."""
    if isinstance(v, float) and math.isinf(v):
        return "unlimited"
    return v


@register_tool
class CheckTierAccessTool(OrigamiTool):
    name = "check_tier_access"
    description = (
        "Return the user's current subscription tier, hard limits "
        "(providers, gateway calls/month, members), and the full feature "
        "matrix showing which features are allowed vs gated. Also lists "
        "what they'd unlock at the next tier — useful when proposing a "
        "build that needs a gated feature so you can show an upgrade prompt."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "feature": {
                "type": "string",
                "description": "Optional: ask about one specific feature (e.g. 'sso', 'ai_context', 'vectorboost'). Returns a focused answer instead of the full matrix.",
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
        from app.services.feature_gate import feature_gate, TierLimits

        feature_filter = params.get("feature")

        try:
            subscription = await feature_gate.get_organization_subscription(
                db, str(org_id)
            )
            tier_enum = subscription["tier"]
            tier_name = (
                tier_enum.value if hasattr(tier_enum, "value") else str(tier_enum)
            )
        except Exception:
            tier_name = "free"

        # Live tier config
        config = TierLimits.TIER_CONFIG.get(tier_enum, TierLimits.TIER_CONFIG[
            list(TierLimits.TIER_CONFIG.keys())[0]
        ])

        limits = {
            "providers": _serialize_limit(config.get("providers")),
            "gateway_calls_per_month": _serialize_limit(
                config.get("gateway_calls_per_month")
            ),
            "members": _serialize_limit(config.get("members")),
        }
        features = config.get("features", {})

        # Build the allowed / gated split with descriptions
        allowed = []
        gated = []
        for key, value in features.items():
            desc = FEATURE_DESCRIPTIONS.get(key, key)
            entry = {"key": key, "description": desc, "value": _serialize_limit(value)}
            if value is False or value == 0:
                gated.append(entry)
            else:
                allowed.append(entry)

        # If they asked about one feature, give a focused answer
        if feature_filter:
            value = features.get(feature_filter)
            if value is None:
                return {
                    "tier": tier_name,
                    "feature": feature_filter,
                    "allowed": False,
                    "note": f"Unknown feature key '{feature_filter}'. Try one of: {list(features.keys())[:10]}",
                }
            return {
                "tier": tier_name,
                "feature": feature_filter,
                "description": FEATURE_DESCRIPTIONS.get(feature_filter, feature_filter),
                "allowed": bool(value) and value != 0,
                "value": _serialize_limit(value),
                "note": _upgrade_hint(tier_name, feature_filter, value),
            }

        # Otherwise return the whole matrix
        next_tier_unlocks = _next_tier_unlocks(tier_name, features)

        return {
            "tier": tier_name,
            "limits": limits,
            "allowed_features": allowed,
            "gated_features": gated,
            "next_tier_unlocks": next_tier_unlocks,
            "note": (
                "Origami should surface gated features via an upgrade-in-place CTA "
                "on the plan card rather than silently degrading."
            ),
        }


def _next_tier_unlocks(current_tier: str, current_features: dict) -> dict[str, Any]:
    """Return the deltas a user gets by upgrading to the next tier."""
    from app.services.feature_gate import SubscriptionTier, TierLimits

    try:
        idx = TIER_ORDER.index(current_tier)
    except ValueError:
        idx = 0

    if idx >= len(TIER_ORDER) - 1:
        return {"next_tier": None, "unlocks": []}

    next_tier_name = TIER_ORDER[idx + 1]
    try:
        next_tier_enum = SubscriptionTier(next_tier_name)
    except Exception:
        return {"next_tier": next_tier_name, "unlocks": []}

    next_config = TierLimits.TIER_CONFIG.get(next_tier_enum)
    if not next_config:
        return {"next_tier": next_tier_name, "unlocks": []}

    next_features = next_config.get("features", {})

    unlocks = []
    for key, next_value in next_features.items():
        current_value = current_features.get(key)
        # Feature becomes allowed
        if (current_value is False or current_value == 0) and next_value not in (False, 0):
            unlocks.append({
                "key": key,
                "description": FEATURE_DESCRIPTIONS.get(key, key),
                "from": _serialize_limit(current_value),
                "to": _serialize_limit(next_value),
            })
        # Limit increases on a quantified feature
        elif isinstance(next_value, (int, float)) and isinstance(current_value, (int, float)):
            if next_value > current_value:
                unlocks.append({
                    "key": key,
                    "description": FEATURE_DESCRIPTIONS.get(key, key),
                    "from": _serialize_limit(current_value),
                    "to": _serialize_limit(next_value),
                })

    return {"next_tier": next_tier_name, "unlocks": unlocks}


def _upgrade_hint(tier_name: str, feature_key: str, value: Any) -> str:
    """Short hint about whether/where this feature unlocks."""
    if value is False or value == 0:
        return (
            f"This feature is gated on the {tier_name} tier. "
            f"Use list_available_models or check_tier_access without a feature "
            f"filter to see which tier unlocks it."
        )
    return f"Available on the {tier_name} tier."
