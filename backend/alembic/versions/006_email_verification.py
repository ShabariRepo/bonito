"""Add email verification fields to users

Revision ID: 006_email_verification
Revises: 005_compliance
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa

revision = "006_email_verification"
down_revision = "005_compliance"
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
