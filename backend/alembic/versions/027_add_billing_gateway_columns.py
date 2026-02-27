"""Add billing tracking columns to gateway_requests.

Adds is_managed and marked_up_cost to gateway_requests table
for managed inference billing tracking (33% markup).

Also adds billing columns to organizations table.

Revision ID: 027_billing_gateway_columns
Revises: 026_bonbon_fields
Create Date: 2026-02-27
"""
from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "027_billing_gateway_columns"
down_revision: Union[str, None] = "026_bonbon_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Gateway request billing tracking
    op.add_column(
        "gateway_requests",
        sa.Column("is_managed", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "gateway_requests",
        sa.Column("marked_up_cost", sa.Float(), nullable=True),
    )

    # Organization agent count tracking for billing
    op.add_column(
        "organizations",
        sa.Column(
            "active_bonbon_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "active_bonobot_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("organizations", "active_bonobot_count")
    op.drop_column("organizations", "active_bonbon_count")
    op.drop_column("gateway_requests", "marked_up_cost")
    op.drop_column("gateway_requests", "is_managed")
