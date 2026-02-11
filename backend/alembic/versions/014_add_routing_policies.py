"""Add routing_policies table

Revision ID: 014_add_routing_policies
Revises: 013_add_updated_at
Create Date: 2026-02-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "014_add_routing_policies"
down_revision = "013_add_updated_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create routing_policies table
    op.create_table(
        "routing_policies",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("strategy", sa.String(length=50), nullable=False),
        sa.Column("models", sa.JSON(), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("api_key_prefix", sa.String(length=50), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    
    # Create indexes
    op.create_index("ix_routing_policies_org_id", "routing_policies", ["org_id"])
    op.create_index("ix_routing_policies_api_key_prefix", "routing_policies", ["api_key_prefix"], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_routing_policies_api_key_prefix", table_name="routing_policies")
    op.drop_index("ix_routing_policies_org_id", table_name="routing_policies")
    
    # Drop table
    op.drop_table("routing_policies")