"""Add updated_at column to users, cloud_providers, policies, routing_rules

Revision ID: 013_add_updated_at
Revises: 012_add_missing_indexes
Create Date: 2026-02-10
"""
from alembic import op
import sqlalchemy as sa

revision = "013_add_updated_at"
down_revision = "012_add_missing_indexes"
branch_labels = None
depends_on = None

_tables = ["users", "cloud_providers", "policies", "routing_rules"]


def upgrade() -> None:
    for table in _tables:
        op.add_column(
            table,
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=True,
            ),
        )


def downgrade() -> None:
    for table in _tables:
        op.drop_column(table, "updated_at")
