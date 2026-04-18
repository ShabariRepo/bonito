"""Fix missing provider_type column in sso_configs

Revision ID: 036_fix_sso_provider_type
Revises: 035_add_agent_secrets_and_kb_compression
Create Date: 2026-04-18

The sso_configs table was created in 019 with provider_type column, but
manual DDL during the Apr 7-10 prod incident may have dropped it.
This migration safely adds it back if missing.

"""
from alembic import op
import sqlalchemy as sa


revision = "036_fix_sso_provider_type"
down_revision = "035_add_agent_secrets_and_kb_compression"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use a DO block to safely check and add the column if missing.
    # PostgreSQL doesn't support ADD COLUMN IF NOT EXISTS natively,
    # so we check information_schema first.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'sso_configs'
                AND column_name = 'provider_type'
            ) THEN
                ALTER TABLE sso_configs
                ADD COLUMN provider_type VARCHAR(50) NOT NULL DEFAULT 'custom';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Don't drop in downgrade — data loss risk
    pass
