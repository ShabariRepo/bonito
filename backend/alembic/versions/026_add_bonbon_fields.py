"""Add BonBon fields to agents table.

Adds columns for Solution Kit template tracking, BonBon configuration,
and chat widget settings.

Revision ID: 026_bonbon_fields
Revises: 025_managed_inference
Create Date: 2026-02-26
"""
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "026_bonbon_fields"
down_revision: Union[str, None] = "025_managed_inference"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # BonBon template tracking
    op.add_column(
        "agents",
        sa.Column("bonbon_template_id", sa.String(length=100), nullable=True),
    )
    # BonBon-specific configuration (tone, company_name, industry)
    op.add_column(
        "agents",
        sa.Column(
            "bonbon_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    # Widget enabled flag
    op.add_column(
        "agents",
        sa.Column(
            "widget_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    # Widget appearance settings (welcome_message, suggested_questions, theme)
    op.add_column(
        "agents",
        sa.Column(
            "widget_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # Index for quick lookups of BonBon agents
    op.create_index(
        "ix_agents_bonbon_template_id",
        "agents",
        ["bonbon_template_id"],
        postgresql_where=sa.text("bonbon_template_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_agents_bonbon_template_id", table_name="agents")
    op.drop_column("agents", "widget_config")
    op.drop_column("agents", "widget_enabled")
    op.drop_column("agents", "bonbon_config")
    op.drop_column("agents", "bonbon_template_id")
