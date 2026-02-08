"""merge phase3 and phase4

Revision ID: 1fb77fbb0284
Revises: 003, 005
Create Date: 2026-02-07 21:47:02.973056
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '1fb77fbb0284'
down_revision: Union[str, None] = ('003', '005')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
