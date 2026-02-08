"""add hashed_password to users

Revision ID: 006_add_hashed_password
Revises: 1fb77fbb0284
Create Date: 2026-02-07
"""
from alembic import op
import sqlalchemy as sa

revision = "006_add_hashed_password"
down_revision = "1fb77fbb0284"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("hashed_password", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "hashed_password")
