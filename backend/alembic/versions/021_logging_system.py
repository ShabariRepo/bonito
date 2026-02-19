"""Add comprehensive logging and observability system

Revision ID: 021_logging
Revises: 020_subscription_tiers
Create Date: 2026-02-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "021_logging"
down_revision = "020_subscription_tiers"
branch_labels = None
depends_on = None


def upgrade():
    # Create log integrations table for external destinations
    op.create_table(
        "log_integrations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("integration_type", sa.String(50), nullable=False),  # datadog, splunk, cloudwatch, etc.
        sa.Column("config", JSONB, nullable=False),  # Integration-specific config
        sa.Column("credentials_path", sa.String(500), nullable=False),  # Vault path for encrypted creds
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("last_test_status", sa.String(50), nullable=True),  # success, failed, pending
        sa.Column("last_test_message", sa.Text, nullable=True),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_log_integrations_org_id", "log_integrations", ["org_id"])
    op.create_index("ix_log_integrations_org_enabled", "log_integrations", ["org_id", "enabled"])

    # Create main platform logs table
    op.create_table(
        "platform_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("log_type", sa.String(50), nullable=False),  # gateway, agent, auth, admin, kb, deployment, billing
        sa.Column("event_type", sa.String(100), nullable=False),  # request, error, login, etc.
        sa.Column("severity", sa.String(20), nullable=False),  # debug, info, warn, error, critical
        sa.Column("trace_id", UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=True),  # model, agent, project, etc.
        sa.Column("action", sa.String(20), nullable=True),  # create, read, update, delete, execute, search
        sa.Column("metadata", JSONB, nullable=True),  # Event-specific structured data
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("cost", sa.Float, nullable=True),
        sa.Column("message", sa.Text, nullable=True),  # Human-readable log message
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Create comprehensive indexes for efficient querying
    op.create_index("ix_platform_logs_org_type_created", "platform_logs", ["org_id", "log_type", "created_at"])
    op.create_index("ix_platform_logs_org_severity_created", "platform_logs", ["org_id", "severity", "created_at"])
    op.create_index("ix_platform_logs_user_created", "platform_logs", ["user_id", "created_at"])
    op.create_index("ix_platform_logs_trace_id", "platform_logs", ["trace_id"])
    op.create_index("ix_platform_logs_resource", "platform_logs", ["resource_type", "resource_id", "created_at"])
    op.create_index("ix_platform_logs_event_type", "platform_logs", ["org_id", "event_type", "created_at"])

    # GIN index for metadata JSONB queries
    op.create_index("ix_platform_logs_metadata_gin", "platform_logs", ["metadata"], postgresql_using="gin")

    # Create log export jobs table for async exports
    op.create_table(
        "log_export_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("export_format", sa.String(20), nullable=False),  # csv, json, parquet
        sa.Column("filters", JSONB, nullable=False),  # Query filters applied
        sa.Column("status", sa.String(20), server_default="'pending'"),  # pending, running, completed, failed
        sa.Column("progress", sa.Integer, server_default="0"),  # 0-100
        sa.Column("total_records", sa.Integer, nullable=True),
        sa.Column("processed_records", sa.Integer, server_default="0"),
        sa.Column("file_path", sa.String(500), nullable=True),  # Path to generated file
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("download_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_log_export_jobs_org_status", "log_export_jobs", ["org_id", "status"])
    op.create_index("ix_log_export_jobs_user_created", "log_export_jobs", ["user_id", "created_at"])

    # Create table for log aggregations and stats (for performance)
    op.create_table(
        "log_aggregations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("date_bucket", sa.Date, nullable=False),  # Daily aggregations
        sa.Column("hour_bucket", sa.Integer, nullable=True),  # 0-23 for hourly granularity
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
    
    # Create unique constraint for aggregation buckets
    op.create_index(
        "ix_log_aggregations_unique_bucket", 
        "log_aggregations", 
        ["org_id", "date_bucket", "hour_bucket", "log_type", "event_type", "severity"], 
        unique=True
    )


def downgrade():
    op.drop_table("log_aggregations")
    op.drop_table("log_export_jobs")
    op.drop_table("platform_logs")
    op.drop_table("log_integrations")