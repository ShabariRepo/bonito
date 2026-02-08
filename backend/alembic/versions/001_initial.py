"""Initial migration

Revision ID: 001
Revises:
Create Date: 2026-02-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "cloud_providers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("provider_type", sa.String(50), nullable=False),
        sa.Column("credentials_encrypted", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "models",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider_id", sa.Uuid(), sa.ForeignKey("cloud_providers.id"), nullable=False),
        sa.Column("model_id", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("capabilities", sa.JSON(), server_default="{}"),
        sa.Column("pricing_info", sa.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "deployments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("model_id", sa.Uuid(), sa.ForeignKey("models.id"), nullable=False),
        sa.Column("provider_id", sa.Uuid(), sa.ForeignKey("cloud_providers.id"), nullable=False),
        sa.Column("config", sa.JSON(), server_default="{}"),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("deployments")
    op.drop_table("models")
    op.drop_table("cloud_providers")
    op.drop_table("organizations")
