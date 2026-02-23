"""merge logging and subscription branches

Revision ID: 9475f6b522e4
Revises: 021_logging, 022_subscription_tiers
Create Date: 2026-02-23 18:49:28.991427
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '9475f6b522e4'
down_revision: Union[str, None] = ('021_logging', '022_subscription_tiers')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
