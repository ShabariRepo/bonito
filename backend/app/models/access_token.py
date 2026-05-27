import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class AccessToken(Base):
    """Personal access tokens (bp-) and project tokens (bj-).

    Single table, discriminated by token_type.
    """

    __tablename__ = "access_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    token_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "personal" or "project"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    token_prefix: Mapped[str] = mapped_column(String(20), nullable=False)  # "bp-a1b2..." or "bj-a1b2..."
    scopes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # ["agents:read", "kb:write"], NULL = full access
    rate_limit: Mapped[int] = mapped_column(Integer, default=120, server_default="120")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_access_tokens_org_id", "org_id"),
        Index("ix_access_tokens_user_id", "user_id"),
        Index("ix_access_tokens_project_id", "project_id"),
    )
