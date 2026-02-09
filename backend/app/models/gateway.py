import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, BigInteger, Index, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class GatewayConfig(Base):
    __tablename__ = "gateway_configs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, unique=True)
    enabled_providers: Mapped[dict] = mapped_column(JSON, default=dict)  # {"aws": True, "azure": False, ...}
    routing_strategy: Mapped[str] = mapped_column(String(50), default="cost-optimized")  # cost-optimized, latency-optimized, balanced, failover
    fallback_models: Mapped[dict] = mapped_column(JSON, default=dict)  # {"gpt-4o": ["claude-3-5-sonnet", "gemini-pro"], ...}
    default_rate_limit: Mapped[int] = mapped_column(Integer, default=60)
    cost_tracking_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    custom_routing_rules: Mapped[dict] = mapped_column(JSON, default=dict)  # Advanced routing configuration
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GatewayRequest(Base):
    __tablename__ = "gateway_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    team_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    key_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("gateway_keys.id"), nullable=True)
    model_requested: Mapped[str] = mapped_column(String(255), nullable=False)
    model_used: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="success")  # success, error, rate_limited
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_gateway_requests_org_created", "org_id", "created_at"),
        Index("ix_gateway_requests_key_created", "key_id", "created_at"),
    )


class GatewayKey(Base):
    __tablename__ = "gateway_keys"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)  # e.g. "bn-abc123..."
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    team_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rate_limit: Mapped[int] = mapped_column(Integer, default=60)  # requests per minute
    allowed_models: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {"models": ["gpt-4o", "claude-3"], "providers": ["aws", "azure"]}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class GatewayRateLimit(Base):
    __tablename__ = "gateway_rate_limits"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    key_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gateway_keys.id"), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("ix_gateway_rate_limits_key_window", "key_id", "window_start"),
    )
