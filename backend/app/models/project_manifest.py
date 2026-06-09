import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class ProjectManifest(Base):
    """Snapshot of a deleted project's structure so it can be skeleton-restored.

    Stored at delete time by delete_project. The restore_project tool reads
    this back and reconstructs the project + agents + connections. KB
    content (documents + chunks) is NOT stored — the user re-uploads after
    restore. Gateway keys are NOT stored — the user re-mints (security).
    """

    __tablename__ = "project_manifests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    deleted_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    restored_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    restored_to_project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        nullable=True
    )
