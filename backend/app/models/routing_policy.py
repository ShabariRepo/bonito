import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, JSON, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class RoutingPolicy(Base):
    __tablename__ = "routing_policies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    strategy: Mapped[str] = mapped_column(String(50), nullable=False)  # cost_optimized, latency_optimized, balanced, failover, ab_test
    models: Mapped[dict] = mapped_column(JSON, default=list)  # array of model configurations
    rules: Mapped[dict] = mapped_column(JSON, default=dict)  # routing rules
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    api_key_prefix: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_routing_policies_org_id", "org_id"),
        Index("ix_routing_policies_api_key_prefix", "api_key_prefix", unique=True),
    )