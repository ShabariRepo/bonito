"""Origami metering — per-turn billing record + per-action audit helper.

Two write paths, both append-only by convention:

1. record_origami_turn() — call ONCE at the end of run_origami_turn with
   the aggregate numbers (cost, tokens, tool count, duration). Writes one
   OrigamiTurnLog row for billing.

2. record_origami_audit() — call once per tool dispatch with the tool name,
   params (redacted), and outcome. Writes one OrigamiAuditLog row.

Read paths in this module:
- count_turns_this_month() for quota enforcement
- get_origami_usage_summary() for the Usage page
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.origami_logs import OrigamiAuditLog, OrigamiTurnLog

logger = logging.getLogger(__name__)


# Params with these names are always redacted before audit-log write,
# regardless of tool schema. Defense-in-depth on top of the per-schema
# allowlist documented in docs/ORIGAMI-MVP-PLAN.md.
_REDACT_PARAM_NAMES = {
    "credentials",
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "private_key",
}


def _redact_params(params: dict[str, Any]) -> dict[str, Any]:
    """Replace cred-looking values with a placeholder."""
    redacted = {}
    for k, v in params.items():
        if k.lower() in _REDACT_PARAM_NAMES:
            redacted[k] = "[REDACTED]"
        else:
            redacted[k] = v
    return redacted


def _billing_period_month_now() -> str:
    """Return current billing period as YYYY-MM."""
    now = datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


async def record_origami_turn(
    *,
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    og_token_id: Optional[uuid.UUID],
    project_id: Optional[uuid.UUID] = None,
    session_id: uuid.UUID,
    conversation_id: Optional[str],
    user_message_preview: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    tool_calls_count: int,
    model_used: Optional[str],
    status: str,
    finish_reason: Optional[str],
    tier_at_time: str,
    duration_ms: Optional[int],
    gateway_request_ids: Optional[list[str]] = None,
) -> Optional[uuid.UUID]:
    """Insert one OrigamiTurnLog row. Returns the new id or None on failure.

    Failure is logged but NEVER raised — billing-log failure must never
    break a user's actual chat turn. We'd rather lose a metering row than
    fail the request.
    """
    try:
        row = OrigamiTurnLog(
            org_id=org_id,
            user_id=user_id,
            og_token_id=og_token_id,
            project_id=project_id,
            session_id=session_id,
            conversation_id=conversation_id,
            user_message_preview=user_message_preview[:500] if user_message_preview else None,
            input_tokens=int(input_tokens or 0),
            output_tokens=int(output_tokens or 0),
            cost_usd=Decimal(str(cost_usd or 0)),
            tool_calls_count=int(tool_calls_count or 0),
            model_used=model_used,
            status=status,
            finish_reason=finish_reason,
            billing_period_month=_billing_period_month_now(),
            tier_at_time=tier_at_time,
            duration_ms=duration_ms,
            gateway_request_ids=(gateway_request_ids or None),
        )
        db.add(row)
        await db.flush()
        # Best-effort commit. Caller may have an outer transaction.
        try:
            await db.commit()
        except Exception:
            await db.rollback()
        return row.id
    except Exception:
        logger.exception("record_origami_turn failed (non-fatal)")
        return None


async def record_origami_audit(
    *,
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    og_token_id: Optional[uuid.UUID],
    project_id: Optional[uuid.UUID] = None,
    session_id: uuid.UUID,
    plan_card_id: Optional[uuid.UUID],
    intent_summary: str,
    tool_name: str,
    tool_params: dict[str, Any],
    tier_at_time: str,
    confirmation: str,
    status: str,
    error: Optional[str] = None,
) -> Optional[uuid.UUID]:
    """Insert one OrigamiAuditLog row. Best-effort, never raises."""
    try:
        row = OrigamiAuditLog(
            org_id=org_id,
            user_id=user_id,
            og_token_id=og_token_id,
            project_id=project_id,
            session_id=session_id,
            plan_card_id=plan_card_id,
            intent_summary=intent_summary[:5000] if intent_summary else "",
            tool_name=tool_name,
            tool_params=_redact_params(tool_params or {}),
            tier_at_time=tier_at_time,
            confirmation=confirmation,
            status=status,
            error=error,
        )
        db.add(row)
        await db.flush()
        try:
            await db.commit()
        except Exception:
            await db.rollback()
        return row.id
    except Exception:
        logger.exception("record_origami_audit failed (non-fatal)")
        return None


# ────────────────────────── Read helpers ──────────────────────────


async def count_turns_this_month(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> int:
    """Count Origami turns for this org in the current billing period.

    Used by orchestrator at the start of each turn to enforce tier quotas.
    """
    period = _billing_period_month_now()
    result = await db.execute(
        select(func.count(OrigamiTurnLog.id)).where(
            OrigamiTurnLog.org_id == org_id,
            OrigamiTurnLog.billing_period_month == period,
            OrigamiTurnLog.status == "success",
        )
    )
    return int(result.scalar_one() or 0)


async def get_origami_usage_summary(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> dict[str, Any]:
    """Per-org Origami usage for the Usage page (UI).

    Returns current-period count + cost, plus a 3-month rolling trend.
    """
    period = _billing_period_month_now()

    # Current period
    current_result = await db.execute(
        select(
            func.count(OrigamiTurnLog.id),
            func.coalesce(func.sum(OrigamiTurnLog.cost_usd), 0),
            func.coalesce(func.sum(OrigamiTurnLog.input_tokens), 0),
            func.coalesce(func.sum(OrigamiTurnLog.output_tokens), 0),
        ).where(
            OrigamiTurnLog.org_id == org_id,
            OrigamiTurnLog.billing_period_month == period,
        )
    )
    current = current_result.one()

    return {
        "current_period": period,
        "turns_used": int(current[0] or 0),
        "cost_usd": float(current[1] or 0),
        "input_tokens": int(current[2] or 0),
        "output_tokens": int(current[3] or 0),
    }


# ────────────────────────── Quota enforcement ──────────────────────────


# Mirrors docs/PRICING-STRATEGY-2026-06.md "Origami COGS & Tier Decision"
TIER_TURN_CAPS = {
    "free": 50,
    "starter": 100,
    "builder": 100,
    "growth": 300,
    "pro": 1000,
    "enterprise": 5000,
    "scale": float("inf"),
}


def get_turn_cap(tier: str) -> int | float:
    """Return monthly turn cap for the given tier name (case-insensitive)."""
    return TIER_TURN_CAPS.get(tier.lower(), TIER_TURN_CAPS["free"])


def get_overage_rate(tier: str) -> float:
    """Per-turn overage rate above the tier base, USD. 0.0 for Free / no-overage tiers."""
    t = tier.lower()
    if t == "enterprise":
        return 0.10
    if t in {"builder", "starter", "growth", "pro"}:
        return 0.12
    return 0.0


async def check_quota(
    db: AsyncSession,
    org_id: uuid.UUID,
    tier: str,
) -> dict[str, Any]:
    """Return current usage vs cap for the org. Caller decides whether to allow.

    {
      "turns_used": 47,
      "cap": 100,
      "remaining": 53,
      "over_cap": False,
      "hard_cap": False,      # True for Free tier — would block
      "overage_rate_usd": 0.12,
    }
    """
    used = await count_turns_this_month(db, org_id)
    cap = get_turn_cap(tier)
    tier_lower = tier.lower()

    if cap == float("inf"):
        return {
            "turns_used": used,
            "cap": None,
            "remaining": None,
            "over_cap": False,
            "hard_cap": False,
            "overage_rate_usd": 0.0,
        }

    remaining = max(0, int(cap) - used)
    over_cap = used >= cap
    hard_cap = tier_lower == "free"

    if tier_lower == "enterprise":
        overage_rate = 0.10
    elif tier_lower in {"builder", "starter", "growth", "pro"}:
        overage_rate = 0.12
    else:
        overage_rate = 0.0

    return {
        "turns_used": used,
        "cap": int(cap),
        "remaining": remaining,
        "over_cap": over_cap,
        "hard_cap": hard_cap and over_cap,
        "overage_rate_usd": overage_rate,
    }


# ── Overage reporting (Stripe metered-billing scaffold) ─────────────────
#
# Pre-Stripe: these functions compute what would be reported. Use them
# from a script for ops visibility OR call them directly when Stripe
# webhook integration lands.
#
# Stripe hook-in (when Stripe is set up):
#   1. Set STRIPE_PRICE_ORIGAMI_OVERAGE in env (a "metered" Stripe Price).
#   2. On the 1st of every month, for every org with subscription_tier in
#      the overage-eligible set, call get_period_overage() for the prior
#      month and POST stripe.SubscriptionItem.create_usage_record with
#      `quantity=overage_turns`, `timestamp=now`. Stripe charges from the
#      Price.
#   3. Or use Stripe's usage-record-summary endpoint for reconciliation.
#
# The math here is the SINGLE source of truth. Do not duplicate it.


async def get_period_overage(
    db: AsyncSession,
    org_id: uuid.UUID,
    tier: str,
    period_start: datetime,
    period_end: datetime,
) -> dict[str, Any]:
    """Compute overage for an arbitrary billing period.

    Returns:
        {
          "tier": "pro",
          "period_start": "...",
          "period_end": "...",
          "turns_total": 1247,
          "tier_cap": 1000,
          "overage_turns": 247,
          "overage_rate_usd": 0.12,
          "overage_amount_usd": 29.64,
        }

    Turns are counted from `origami_turn_log` filtered by org_id and the
    period bounds. Period bounds are inclusive of start, exclusive of end
    (standard SQL half-open interval).
    """
    result = await db.execute(
        select(func.count(OrigamiTurnLog.id)).where(
            OrigamiTurnLog.org_id == org_id,
            OrigamiTurnLog.created_at >= period_start,
            OrigamiTurnLog.created_at < period_end,
        )
    )
    total_turns = int(result.scalar_one() or 0)

    cap = get_turn_cap(tier)
    overage_turns = max(0, total_turns - int(cap)) if cap != float("inf") else 0
    overage_rate = get_overage_rate(tier)
    overage_amount = round(overage_turns * overage_rate, 2)

    return {
        "tier": tier.lower(),
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "turns_total": total_turns,
        "tier_cap": int(cap) if cap != float("inf") else None,
        "overage_turns": overage_turns,
        "overage_rate_usd": overage_rate,
        "overage_amount_usd": overage_amount,
    }


async def get_current_month_overage(
    db: AsyncSession,
    org_id: uuid.UUID,
    tier: str,
) -> dict[str, Any]:
    """Convenience: overage for the current calendar month so far (UTC)."""
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # End-of-month: jump to next month's day 1
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return await get_period_overage(db, org_id, tier, start, end)
