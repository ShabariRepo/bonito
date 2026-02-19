"""Add platform logging and observability tables

Revision ID: 021_add_logging_tables
Revises: 020_add_bonobot_tables
Create Date: 2026-02-19

Adds tables for the hierarchical logging and observability system:
- log_integrations: External log destination configs per org
- platform_logs: Main event log table with hierarchical structure
- log_export_jobs: Async export job tracking
- log_aggregations: Pre-computed stats for dashboard performance
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "021_add_logging_tables"
down_revision = "020_add_bonobot_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- log_integrations --
    op.create_table(
        "log_integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("integration_type", sa.String(50), nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False),
        sa.Column("credentials_path", sa.String(500), nullable=False),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("last_test_status", sa.String(50), nullable=True),
        sa.Column("last_test_message", sa.Text, nullable=True),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_log_integrations_org_id", "log_integrations", ["org_id"])
    op.create_index("ix_log_integrations_org_enabled", "log_integrations", ["org_id", "enabled"])

    # -- platform_logs --
    op.create_table(
        "platform_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("log_type", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("action", sa.String(20), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("cost", sa.Float, nullable=True),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_platform_logs_org_type_created", "platform_logs", ["org_id", "log_type", "created_at"])
    op.create_index("ix_platform_logs_org_severity_created", "platform_logs", ["org_id", "severity", "created_at"])
    op.create_index("ix_platform_logs_user_created", "platform_logs", ["user_id", "created_at"])
    op.create_index("ix_platform_logs_trace_id", "platform_logs", ["trace_id"])
    op.create_index("ix_platform_logs_resource", "platform_logs", ["resource_type", "resource_id", "created_at"])
    op.create_index("ix_platform_logs_event_type", "platform_logs", ["org_id", "event_type", "created_at"])
    op.create_index("ix_platform_logs_metadata_gin", "platform_logs", ["metadata"], postgresql_using="gin")

    # -- log_export_jobs --
    op.create_table(
        "log_export_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("export_format", sa.String(20), nullable=False),
        sa.Column("filters", postgresql.JSONB, nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("progress", sa.Integer, server_default="0"),
        sa.Column("total_records", sa.Integer, nullable=True),
        sa.Column("processed_records", sa.Integer, server_default="0"),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("download_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_log_export_jobs_org_status", "log_export_jobs", ["org_id", "status"])
    op.create_index("ix_log_export_jobs_user_created", "log_export_jobs", ["user_id", "created_at"])

    # -- log_aggregations --
    op.create_table(
        "log_aggregations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("date_bucket", sa.Date, nullable=False),
        sa.Column("hour_bucket", sa.Integer, nullable=True),
        sa.Column("log_type", sa.String(50), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=True),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("log_count", sa.Integer, server_default="0"),
        sa.Column("error_count", sa.Integer, server_default="0"),
        sa.Column("total_duration_ms", sa.BigInteger, nullable=True),
        sa.Column("total_cost", sa.Float, nullable=True),
        sa.Column("unique_users", sa.Integer, nullable=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_log_aggregations_org_date", "log_aggregations", ["org_id", "date_bucket"])
    op.create_index("ix_log_aggregations_org_type_date", "log_aggregations", ["org_id", "log_type", "date_bucket"])
    op.create_index(
        "ix_log_aggregations_unique_bucket",
        "log_aggregations",
        ["org_id", "date_bucket", "hour_bucket", "log_type", "event_type", "severity"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("log_aggregations")
    op.drop_table("log_export_jobs")
    op.drop_table("platform_logs")
    op.drop_table("log_integrations")
