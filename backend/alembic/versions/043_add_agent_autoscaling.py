"""Add agent autoscaling (HPA) columns and scaling_events table

Adds autoscale_enabled, autoscale_config, primary_agent_id, replica_index
to the agents table, and creates agent_scaling_events for audit trail.

Revision ID: 043_add_agent_autoscaling
Revises: 042_merge_heads
Create Date: 2026-05-25
"""
import sqlalchemy as sa
from alembic import op


revision = "043_add_agent_autoscaling"
down_revision = "042_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add autoscaling columns to agents table
    op.add_column("agents", sa.Column("autoscale_enabled", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("agents", sa.Column("autoscale_config", sa.JSON(), nullable=True))
    op.add_column("agents", sa.Column("primary_agent_id", sa.Uuid(), nullable=True))
    op.add_column("agents", sa.Column("replica_index", sa.Integer(), nullable=True))

    # FK and index for replica lookups
    op.create_foreign_key(
        "fk_agents_primary_agent_id",
        "agents", "agents",
        ["primary_agent_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_index("idx_agents_primary_agent_id", "agents", ["primary_agent_id"])

    # Create scaling events table
    op.create_table(
        "agent_scaling_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("previous_capacity", sa.Integer(), nullable=False),
        sa.Column("new_capacity", sa.Integer(), nullable=False),
        sa.Column("replica_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trigger_utilization", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_agent_scaling_events_agent_id", "agent_scaling_events", ["agent_id"])


def downgrade() -> None:
    op.drop_table("agent_scaling_events")
    op.drop_index("idx_agents_primary_agent_id", table_name="agents")
    op.drop_constraint("fk_agents_primary_agent_id", "agents", type_="foreignkey")
    op.drop_column("agents", "replica_index")
    op.drop_column("agents", "primary_agent_id")
    op.drop_column("agents", "autoscale_config")
    op.drop_column("agents", "autoscale_enabled")
