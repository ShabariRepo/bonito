"""Add email verification fields to users

Revision ID: 011_email_verification
Revises: 010_gateway_enhancements
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa

revision = "011_email_verification"
down_revision = "010_gateway_enhancements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("users", sa.Column("verification_token", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("reset_token", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "reset_token")
    op.drop_column("users", "verification_token")
    op.drop_column("users", "email_verified")
