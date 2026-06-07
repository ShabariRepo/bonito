"""SQLAlchemy model for origami_messages (migration 048)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class OrigamiMessage(Base):
    """One row per user-visible chat message — user prompts, assistant
    replies, plan cards."""

    __tablename__ = "origami_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    conversation_id: Mapped[str] = mapped_column(String(255), nullable=False)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # user | assistant | plan | system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    synthesized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_origami_messages_org_conversation",
            "org_id", "conversation_id", "created_at",
        ),
        Index("ix_origami_messages_user_time", "user_id", "created_at"),
        Index("ix_origami_messages_conv", "conversation_id"),
    )
