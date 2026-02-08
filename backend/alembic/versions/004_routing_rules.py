"""Add routing_rules table

Revision ID: 004
Revises: 001
Create Date: 2026-02-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "routing_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("strategy", sa.String(50), nullable=False),
        sa.Column("conditions_json", sa.JSON(), server_default="{}"),
        sa.Column("priority", sa.Integer(), server_default="0"),
        sa.Column("enabled", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("routing_rules")
