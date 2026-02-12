"""Add verification_token_expires_at and reset_token_expires_at to users

Revision ID: 015_token_expiry
Revises: 014_add_routing_policies
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa

revision = "015_token_expiry"
down_revision = "014_add_routing_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # These columns exist in the User model but were never migrated.
    # Using IF NOT EXISTS equivalent via batch_alter or try/except since
    # production DB already has them from a manual fix.
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = [c["name"] for c in inspector.get_columns("users")]

    if "verification_token_expires_at" not in existing:
        op.add_column("users", sa.Column("verification_token_expires_at", sa.DateTime(timezone=True), nullable=True))
    if "reset_token_expires_at" not in existing:
        op.add_column("users", sa.Column("reset_token_expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "reset_token_expires_at")
    op.drop_column("users", "verification_token_expires_at")
