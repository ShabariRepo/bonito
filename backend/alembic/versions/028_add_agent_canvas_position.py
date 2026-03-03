"""Add canvas_position to agents table.

Stores agent node positions on the React Flow canvas so
they persist across page reloads.

Revision ID: 028_agent_canvas_position
Revises: 027_billing_gateway_columns
Create Date: 2026-03-03
"""
from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "028_agent_canvas_position"
down_revision: Union[str, None] = "027_billing_gateway_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("canvas_position", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("agents", "canvas_position")
