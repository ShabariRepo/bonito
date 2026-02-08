"""Add notifications, alert_rules, notification_preferences tables

Revision ID: 008_notifications
Revises: 007_onboarding
Create Date: 2026-02-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "009_notifications"
down_revision = "008_gateway"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_org_id", "notifications", ["org_id"])

    op.create_table(
        "alert_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False, server_default="in_app"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_alert_rules_org_id", "alert_rules", ["org_id"])

    op.create_table(
        "notification_preferences",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("weekly_digest", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("cost_alerts", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("compliance_alerts", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("model_updates", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade():
    op.drop_table("notification_preferences")
    op.drop_table("alert_rules")
    op.drop_table("notifications")
