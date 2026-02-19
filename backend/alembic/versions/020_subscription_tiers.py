"""Add subscription tier system

Revision ID: 020_subscription_tiers
Revises: 019_add_sso_config
Create Date: 2026-02-19

Adds subscription tier fields to organizations table and creates subscription_history table.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "020_subscription_tiers"
down_revision = "019_add_sso_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add subscription tier fields to organizations table
    op.add_column("organizations", sa.Column("subscription_tier", sa.String(50), nullable=False, server_default="free"))
    op.add_column("organizations", sa.Column("subscription_status", sa.String(50), nullable=False, server_default="active"))
    op.add_column("organizations", sa.Column("subscription_updated_at", sa.DateTime(timezone=True), nullable=True))
    
    # Add Bonobot fields to organizations table
    op.add_column("organizations", sa.Column("bonobot_plan", sa.String(50), nullable=False, server_default="none"))
    op.add_column("organizations", sa.Column("bonobot_agent_limit", sa.Integer(), nullable=False, server_default="0"))

    # Create subscription_history table
    op.create_table(
        "subscription_history",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_tier", sa.String(50), nullable=True),
        sa.Column("new_tier", sa.String(50), nullable=False),
        sa.Column("previous_status", sa.String(50), nullable=True),
        sa.Column("new_status", sa.String(50), nullable=False),
        sa.Column("previous_bonobot_plan", sa.String(50), nullable=True),
        sa.Column("new_bonobot_plan", sa.String(50), nullable=False, server_default="none"),
        sa.Column("previous_bonobot_agent_limit", sa.Integer(), nullable=True),
        sa.Column("new_bonobot_agent_limit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("changed_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for subscription_history
    op.create_index("ix_subscription_history_org_id", "subscription_history", ["org_id"])
    op.create_index("ix_subscription_history_created_at", "subscription_history", ["created_at"])


def downgrade() -> None:
    # Drop subscription_history table
    op.drop_index("ix_subscription_history_created_at", table_name="subscription_history")
    op.drop_index("ix_subscription_history_org_id", table_name="subscription_history")
    op.drop_table("subscription_history")
    
    # Remove subscription fields from organizations
    op.drop_column("organizations", "bonobot_agent_limit")
    op.drop_column("organizations", "bonobot_plan")
    op.drop_column("organizations", "subscription_updated_at")
    op.drop_column("organizations", "subscription_status")
    op.drop_column("organizations", "subscription_tier")