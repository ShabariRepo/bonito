"""SQLAlchemy models for Origami audit + turn logs (migration 046)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class OrigamiAuditLog(Base):
    """Per-tool-call audit record. Append-only by app convention.

    One row every time an Origami tool fires inside a turn. For forensics,
    compliance, abuse investigation. NOT used for billing (see
    OrigamiTurnLog for that).
    """

    __tablename__ = "origami_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    og_token_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("access_tokens.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    plan_card_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    intent_summary: Mapped[str] = mapped_column(Text, nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    tier_at_time: Mapped[str] = mapped_column(String(50), nullable=False)
    confirmation: Mapped[str] = mapped_column(String(50), nullable=False)
    # auto | user_clicked | upgrade_then_auto
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    # success | failed | partial
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_origami_audit_org_time", "org_id", "created_at"),
        Index("ix_origami_audit_user", "user_id", "created_at"),
        Index("ix_origami_audit_token", "og_token_id"),
        Index("ix_origami_audit_project", "project_id", "created_at"),
    )


class OrigamiTurnLog(Base):
    """Per-turn billing record. One row per user-visible chat exchange.

    Carries the user's org_id (for billing attribution) and the cost summed
    across all internal gateway calls. Powers the Usage page and tier
    quota enforcement (50/100/300/1000/5000 turns per month).
    """

    __tablename__ = "origami_turn_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    og_token_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("access_tokens.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    conversation_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_message_preview: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Cache token split (Anthropic prompt caching). Used by the admin billing
    # dashboard to compute the REAL cache-discounted cost / margin. cost_usd
    # below stays full-price (conservative) for the spend cap.
    cache_read_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    cache_write_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False, default=Decimal(0)
    )
    tool_calls_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_used: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    # success | failed | over_quota
    finish_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    billing_period_month: Mapped[str] = mapped_column(String(7), nullable=False)
    # 'YYYY-MM'
    tier_at_time: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gateway_request_ids: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_origami_turn_org_period", "org_id", "billing_period_month"),
        Index("ix_origami_turn_user_time", "user_id", "created_at"),
        Index("ix_origami_turn_token", "og_token_id"),
        Index("ix_origami_turn_project_period", "project_id", "billing_period_month"),
    )
