"""In-memory plan-card store with TTL.

Origami's plan-card lifecycle is short (created → user confirms within
seconds → executed). Using Redis or DB for these would be overkill — a
process-local dict with TTL is sufficient for Phase 2.

Trade-off: if the backend process restarts between plan creation and
user confirmation, the plan is lost. The frontend gets a 404 on
execute_plan and Origami re-pitches. Acceptable for MVP.

Phase 3 upgrade path: move to Redis when we have multiple backend
workers OR when we want plans to survive a restart.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Optional

from app.schemas.origami_plan import PlanCard, PlanCardStatus

logger = logging.getLogger(__name__)


PLAN_TTL_SECONDS = 600  # 10 minutes is generous — typical use is < 30s


_store: dict[str, tuple[PlanCard, float, dict[str, Any]]] = {}
# value tuple: (plan_card, expires_at_epoch, owner_context)
# owner_context carries: { user_id, org_id, project_id, conversation_id, message }


def _now() -> float:
    return time.time()


def _evict_expired() -> None:
    now = _now()
    stale = [k for k, (_pc, exp, _ctx) in _store.items() if exp < now]
    for k in stale:
        _store.pop(k, None)


def save_plan(
    *,
    plan: PlanCard,
    user_id: uuid.UUID,
    org_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[str] = None,
    user_message: str = "",
) -> None:
    """Save a plan card for later execute_plan. Auto-evicts expired ones."""
    _evict_expired()
    _store[str(plan.id)] = (
        plan,
        _now() + PLAN_TTL_SECONDS,
        {
            "user_id": user_id,
            "org_id": org_id,
            "project_id": project_id,
            "conversation_id": conversation_id,
            "user_message": user_message,
        },
    )


def get_plan(plan_id: str) -> Optional[tuple[PlanCard, dict[str, Any]]]:
    """Look up a plan and its owner context. Returns None if missing / expired."""
    _evict_expired()
    entry = _store.get(plan_id)
    if not entry:
        return None
    plan, _exp, ctx = entry
    return plan, ctx


def update_status(plan_id: str, status: PlanCardStatus) -> Optional[PlanCard]:
    """Transition a plan's status in-place."""
    entry = _store.get(plan_id)
    if not entry:
        return None
    plan, exp, ctx = entry
    plan.status = status
    _store[plan_id] = (plan, exp, ctx)
    return plan


def delete_plan(plan_id: str) -> None:
    _store.pop(plan_id, None)
