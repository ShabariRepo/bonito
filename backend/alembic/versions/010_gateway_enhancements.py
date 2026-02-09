"""Add gateway configuration and key scoping

Revision ID: 010_gateway_enhancements
Revises: 009_notifications
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "010_gateway_enhancements"
down_revision = "009_notifications"
branch_labels = None
depends_on = None


def upgrade():
    # Add gateway_configs table
    op.create_table(
        "gateway_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, unique=True),
        sa.Column("enabled_providers", JSON(), server_default="{}"),
        sa.Column("routing_strategy", sa.String(50), server_default="'cost-optimized'"),
        sa.Column("fallback_models", JSON(), server_default="{}"),
        sa.Column("default_rate_limit", sa.Integer, server_default="60"),
        sa.Column("cost_tracking_enabled", sa.Boolean, server_default="true"),
        sa.Column("custom_routing_rules", JSON(), server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Add allowed_models column to gateway_keys
    op.add_column("gateway_keys", sa.Column("allowed_models", JSON(), nullable=True))


def downgrade():
    op.drop_column("gateway_keys", "allowed_models")
    op.drop_table("gateway_configs")