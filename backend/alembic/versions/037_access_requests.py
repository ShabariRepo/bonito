"""add_access_requests

Revision ID: 037_access_requests
Revises: cfc22bba5dd4
Create Date: 2026-04-20 14:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '037_access_requests'
down_revision: Union[str, Sequence[str], None] = '036_fix_sso_provider_type'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create access_requests enum type (idempotent — may already exist from a partial run)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'access_request_status') THEN
                CREATE TYPE access_request_status AS ENUM ('pending', 'approved', 'denied');
            END IF;
        END $$;
    """)

    op.create_table(
        'access_requests',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('company', sa.String(255), nullable=True),
        sa.Column('use_case', sa.Text, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('invite_code', sa.String(16), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processed_by', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )

    op.create_index('idx_access_requests_email', 'access_requests', ['email'])
    op.create_index('idx_access_requests_status', 'access_requests', ['status'])


def downgrade() -> None:
    op.drop_index('idx_access_requests_status', 'access_requests')
    op.drop_index('idx_access_requests_email', 'access_requests')
    op.drop_table('access_requests')
    op.execute("DROP TYPE IF EXISTS access_request_status")
