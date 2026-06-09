"""Origami plan-card schemas.

Plan cards are the safety net for write tools. When Origami wants to mutate
state (create_kb, create_agent, link_kb_to_agent, etc.), it does NOT execute
immediately — it builds a PlanCard, emits a `plan_ready` SSE event, and
waits for the user to click Deploy. Only then does the orchestrator run
the buffered tool calls.

Shape mirrors docs/ORIGAMI-MVP-PLAN.md "The plan card" section.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class PlanCardStatus(str, Enum):
    """Lifecycle of a plan card."""

    DRAFT = "draft"                                # being built (orchestrator still streaming)
    AWAITING_CONFIRMATION = "awaiting_confirmation"  # rendered, waiting for user click
    EXECUTING = "executing"                        # Deploy clicked, running tools
    DONE = "done"                                  # all tools succeeded
    FAILED = "failed"                              # at least one tool failed
    CANCELLED = "cancelled"                        # user clicked Cancel


class PlanChange(BaseModel):
    """One concrete action inside a plan card — a single tool call."""

    action: str = Field(description="Tool name, e.g. 'create_kb' or 'create_agent'")
    params: dict[str, Any] = Field(description="Tool params (sanitized; org_id stripped)")
    summary: Optional[str] = Field(
        default=None,
        description="One-line human-readable explanation of what this change does",
    )
    is_write: bool = Field(default=True, description="True for state-mutating actions")


class TierImpact(BaseModel):
    """How the plan affects the user's tier limits / billing."""

    summary: str = Field(description="Plain-language tier impact, e.g. 'uses 1 of 2 KBs on Builder'")
    requires_upgrade: bool = Field(default=False, description="True if the plan is gated above current tier")
    blocking_features: list[str] = Field(default_factory=list, description="Feature keys that are gated")
    upgrade_to_tier: Optional[str] = Field(default=None, description="Minimum tier that unlocks this plan")


class PlanCard(BaseModel):
    """The structured object emitted by the orchestrator BEFORE executing writes.

    Frontend renders this as the inline plan card with Deploy / Edit / Cancel.
    """

    model_config = ConfigDict(use_enum_values=True)

    id: uuid.UUID = Field(description="Stable id used to confirm / cancel / look up later")
    session_id: uuid.UUID = Field(description="Origami session this plan belongs to")
    intent: str = Field(description="What the user is trying to do, in plain language")
    changes: list[PlanChange] = Field(description="Ordered list of tool calls to run")
    tier_impact: Optional[TierImpact] = Field(default=None)
    estimated_cost_usd_monthly: Optional[float] = Field(
        default=None,
        description="Best-effort recurring cost estimate (token budget + KB storage)",
    )
    status: PlanCardStatus = Field(default=PlanCardStatus.DRAFT)
    created_at: Optional[datetime] = None


class ExecutePlanRequest(BaseModel):
    """Body for POST /api/origami/execute_plan."""

    plan_card_id: str = Field(description="ID of the plan card to execute (from plan_ready event)")
    conversation_id: Optional[str] = None
    project_id: Optional[str] = None


class CancelPlanRequest(BaseModel):
    """Body for DELETE /api/origami/plan."""

    plan_card_id: str
