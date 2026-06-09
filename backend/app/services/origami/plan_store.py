"""Redis-backed plan-card store with TTL.

Origami's orchestrator can run on any uvicorn worker, but `execute_plan`
might be served by a DIFFERENT worker — so an in-memory dict caused
cross-worker plan_not_found bugs. Using Redis means every worker sees
the same plan store.

Key shape: `origami:plan:{plan_id}` → JSON {plan, owner_context}
TTL: 10 minutes (the user's confirm window). Plans expire automatically.

If Redis is unavailable, the helpers fall back to an in-process dict.
This is acceptable for dev tests / single-worker runs but logs warnings.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Optional

from app.schemas.origami_plan import PlanCard, PlanCardStatus

logger = logging.getLogger(__name__)


PLAN_TTL_SECONDS = 600
KEY_PREFIX = "origami:plan:"


# Process-local fallback if Redis is down. Same shape as before.
_LOCAL_FALLBACK: dict[str, tuple[PlanCard, float, dict[str, Any]]] = {}


def _key(plan_id: str) -> str:
    return f"{KEY_PREFIX}{plan_id}"


def _serialize_owner_ctx(ctx: dict[str, Any]) -> dict[str, Any]:
    """UUIDs → strings so we can JSON encode."""
    return {k: (str(v) if isinstance(v, uuid.UUID) else v) for k, v in ctx.items()}


def _deserialize_owner_ctx(raw: dict[str, Any]) -> dict[str, Any]:
    """Strings → UUIDs for fields the orchestrator expects as UUIDs."""
    result: dict[str, Any] = dict(raw)
    for k in ("user_id", "org_id", "project_id"):
        v = result.get(k)
        if isinstance(v, str):
            try:
                result[k] = uuid.UUID(v)
            except ValueError:
                pass
    return result


async def _get_redis_async():
    """Return a redis.asyncio client if reachable, else None."""
    try:
        from app.core.redis import get_redis
        client = await get_redis()
        await client.ping()
        return client
    except Exception as e:
        logger.warning(f"Origami plan_store: Redis unreachable, using local fallback ({e})")
        return None


async def save_plan(
    *,
    plan: PlanCard,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[str] = None,
    user_message: str = "",
) -> None:
    """Persist a plan card for later execute_plan."""
    owner_ctx = {
        "user_id": user_id,
        "org_id": org_id,
        "project_id": project_id,
        "conversation_id": conversation_id,
        "user_message": user_message,
    }
    payload = json.dumps({
        "plan": plan.model_dump(mode="json"),
        "owner": _serialize_owner_ctx(owner_ctx),
    })

    r = await _get_redis_async()
    if r is None:
        # Process-local fallback
        _LOCAL_FALLBACK[str(plan.id)] = (plan, time.time() + PLAN_TTL_SECONDS, owner_ctx)
        return

    try:
        await r.setex(_key(str(plan.id)), PLAN_TTL_SECONDS, payload)
    except Exception:
        logger.exception("Origami plan_store: Redis setex failed, falling back")
        _LOCAL_FALLBACK[str(plan.id)] = (plan, time.time() + PLAN_TTL_SECONDS, owner_ctx)


async def get_plan(plan_id: str) -> Optional[tuple[PlanCard, dict[str, Any]]]:
    """Look up a plan and its owner context. Returns None if missing / expired."""
    r = await _get_redis_async()
    if r is not None:
        try:
            raw = await r.get(_key(plan_id))
            if raw is not None:
                if isinstance(raw, (bytes, bytearray)):
                    raw = raw.decode("utf-8")
                payload = json.loads(raw)
                plan = PlanCard.model_validate(payload["plan"])
                owner = _deserialize_owner_ctx(payload.get("owner") or {})
                return plan, owner
        except Exception:
            logger.exception("Origami plan_store: Redis get failed, checking fallback")

    # Fallback
    entry = _LOCAL_FALLBACK.get(plan_id)
    if not entry:
        return None
    plan, exp, ctx = entry
    if exp < time.time():
        _LOCAL_FALLBACK.pop(plan_id, None)
        return None
    return plan, ctx


async def update_status(plan_id: str, status: PlanCardStatus) -> Optional[PlanCard]:
    """Transition a plan's status in-place."""
    entry = await get_plan(plan_id)
    if not entry:
        return None
    plan, ctx = entry
    plan.status = status

    # Re-persist
    await save_plan(
        plan=plan,
        user_id=ctx["user_id"],
        org_id=ctx["org_id"],
        project_id=ctx.get("project_id"),
        conversation_id=ctx.get("conversation_id"),
        user_message=ctx.get("user_message", ""),
    )
    return plan


async def delete_plan(plan_id: str) -> None:
    r = await _get_redis_async()
    if r is not None:
        try:
            await r.delete(_key(plan_id))
        except Exception:
            logger.exception("Origami plan_store: Redis delete failed")
    _LOCAL_FALLBACK.pop(plan_id, None)
