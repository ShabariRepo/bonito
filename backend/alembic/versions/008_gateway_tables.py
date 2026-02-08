"""Add gateway tables

Revision ID: 008_gateway
Revises: 007_onboarding
Create Date: 2026-02-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "008_gateway"
down_revision = "007_onboarding"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "gateway_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("key_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("team_id", sa.String(255), nullable=True),
        sa.Column("rate_limit", sa.Integer, nullable=False, server_default="60"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "gateway_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("team_id", sa.String(255), nullable=True),
        sa.Column("key_id", UUID(as_uuid=True), sa.ForeignKey("gateway_keys.id"), nullable=True),
        sa.Column("model_requested", sa.String(255), nullable=False),
        sa.Column("model_used", sa.String(255), nullable=True),
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column("input_tokens", sa.Integer, server_default="0"),
        sa.Column("output_tokens", sa.Integer, server_default="0"),
        sa.Column("cost", sa.Float, server_default="0"),
        sa.Column("latency_ms", sa.Integer, server_default="0"),
        sa.Column("status", sa.String(50), server_default="'success'"),
        sa.Column("error_message", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_gateway_requests_org_created", "gateway_requests", ["org_id", "created_at"])
    op.create_index("ix_gateway_requests_key_created", "gateway_requests", ["key_id", "created_at"])

    op.create_table(
        "gateway_rate_limits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("key_id", UUID(as_uuid=True), sa.ForeignKey("gateway_keys.id"), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer, server_default="0"),
    )
    op.create_index("ix_gateway_rate_limits_key_window", "gateway_rate_limits", ["key_id", "window_start"])


def downgrade():
    op.drop_table("gateway_rate_limits")
    op.drop_table("gateway_requests")
    op.drop_table("gateway_keys")
