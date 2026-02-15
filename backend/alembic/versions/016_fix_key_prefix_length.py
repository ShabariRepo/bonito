"""Fix gateway_keys.key_prefix column length (12 -> 20)

The generate_api_key() produces "bn-xxxxxx..." (15 chars) but the column
was created as String(12). Also ensures allowed_models column exists.

Revision ID: 016_fix_key_prefix
Revises: 015_token_expiry
Create Date: 2026-02-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = "016_fix_key_prefix"
down_revision = "015_token_expiry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix key_prefix column length
    op.alter_column(
        "gateway_keys",
        "key_prefix",
        type_=sa.String(20),
        existing_type=sa.String(12),
        existing_nullable=False,
    )
    
    # Ensure allowed_models column exists (migration 010 may not have run)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = [c["name"] for c in inspector.get_columns("gateway_keys")]
    if "allowed_models" not in existing:
        op.add_column("gateway_keys", sa.Column("allowed_models", JSON(), nullable=True))


def downgrade() -> None:
    op.alter_column(
        "gateway_keys",
        "key_prefix",
        type_=sa.String(12),
        existing_type=sa.String(20),
        existing_nullable=False,
    )
