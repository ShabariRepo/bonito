import uuid
from datetime import datetime, date
from typing import Optional, Dict, Any

from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, BigInteger, Index, Boolean, Text, Date
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class LogIntegration(Base):
    """External log destination configurations per organization."""
    
    __tablename__ = "log_integrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    integration_type: Mapped[str] = mapped_column(String(50), nullable=False)  # datadog, splunk, cloudwatch, etc.
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)  # Integration-specific config
    credentials_path: Mapped[str] = mapped_column(String(500), nullable=False)  # Vault path for encrypted creds
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_test_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # success, failed, pending
    last_test_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_test_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_log_integrations_org_id", "org_id"),
        Index("ix_log_integrations_org_enabled", "org_id", "enabled"),
    )


class PlatformLog(Base):
    """Main hierarchical logging table for all platform events."""
    
    __tablename__ = "platform_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    log_type: Mapped[str] = mapped_column(String(50), nullable=False)  # gateway, agent, auth, admin, kb, deployment, billing
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)  # request, error, login, etc.
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # debug, info, warn, error, critical
    trace_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # model, agent, project, etc.
    action: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # create, read, update, delete, execute, search
<<<<<<< HEAD
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)  # Event-specific structured data
=======
    event_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)  # Event-specific structured data
>>>>>>> main
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Human-readable log message
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_platform_logs_org_type_created", "org_id", "log_type", "created_at"),
        Index("ix_platform_logs_org_severity_created", "org_id", "severity", "created_at"),
        Index("ix_platform_logs_user_created", "user_id", "created_at"),
        Index("ix_platform_logs_trace_id", "trace_id"),
        Index("ix_platform_logs_resource", "resource_type", "resource_id", "created_at"),
        Index("ix_platform_logs_event_type", "org_id", "event_type", "created_at"),
        Index("ix_platform_logs_metadata_gin", "metadata", postgresql_using="gin"),
    )


class LogExportJob(Base):
    """Async log export job tracking."""
    
    __tablename__ = "log_export_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    export_format: Mapped[str] = mapped_column(String(20), nullable=False)  # csv, json, parquet
    filters: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)  # Query filters applied
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, running, completed, failed
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    total_records: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    processed_records: Mapped[int] = mapped_column(Integer, default=0)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # Path to generated file
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    download_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_log_export_jobs_org_status", "org_id", "status"),
        Index("ix_log_export_jobs_user_created", "user_id", "created_at"),
    )


class LogAggregation(Base):
    """Pre-computed log aggregations for dashboard performance."""
    
    __tablename__ = "log_aggregations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    date_bucket: Mapped[date] = mapped_column(Date, nullable=False)  # Daily aggregations
    hour_bucket: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0-23 for hourly granularity
    log_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    event_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    log_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    total_duration_ms: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    total_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unique_users: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_log_aggregations_org_date", "org_id", "date_bucket"),
        Index("ix_log_aggregations_org_type_date", "org_id", "log_type", "date_bucket"),
        Index(
            "ix_log_aggregations_unique_bucket", 
            "org_id", "date_bucket", "hour_bucket", "log_type", "event_type", "severity", 
            unique=True
        ),
    )