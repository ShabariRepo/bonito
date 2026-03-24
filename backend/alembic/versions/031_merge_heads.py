"""merge heads

Revision ID: 031_merge_heads
Revises: 030_add_github_app_tables, 0b1b3e3d1a88
Create Date: 2026-03-24 19:20:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '031_merge_heads'
down_revision: Union[str, None] = ('030_add_github_app_tables', '0b1b3e3d1a88')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No changes needed for merge
    pass


def downgrade() -> None:
    # No changes needed for merge
    pass