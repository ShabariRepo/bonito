"""Add managed inference columns to cloud_providers.

Tracks whether a provider connection uses Bonito-managed keys,
along with usage metrics for billing.

Revision ID: 025_managed_inference
Revises: 024_agent_mcp_servers
Create Date: 2026-02-27
"""
from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "025_managed_inference"
down_revision: Union[str, None] = "024_agent_mcp_servers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cloud_providers",
        sa.Column("is_managed", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "cloud_providers",
        sa.Column("managed_usage_tokens", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "cloud_providers",
        sa.Column("managed_usage_cost", sa.Numeric(10, 4), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("cloud_providers", "managed_usage_cost")
    op.drop_column("cloud_providers", "managed_usage_tokens")
    op.drop_column("cloud_providers", "is_managed")
