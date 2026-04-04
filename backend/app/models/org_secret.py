import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class OrgSecret(Base):
    """
    Org-scoped key-value secret store.

    Stores metadata about secrets (name, description, vault reference) in Postgres.
    Actual secret values are stored in Vault at: secret/orgs/{org_id}/secrets/{name}
    """
    __tablename__ = "org_secrets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. META_ACCESS_TOKEN
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vault_ref: Mapped[str] = mapped_column(String(512), nullable=False)  # vault path reference

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_org_secrets_org_id", "org_id"),
        Index("uq_org_secrets_org_name", "org_id", "name", unique=True),
    )
