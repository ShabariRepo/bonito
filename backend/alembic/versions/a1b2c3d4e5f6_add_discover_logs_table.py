"""add_discover_logs_table

Revision ID: a1b2c3d4e5f6
Revises: cfc22bba5dd4
Create Date: 2026-05-15 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'cfc22bba5dd4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'discover_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('result_id', sa.String(36), nullable=False, index=True),
        sa.Column('company_name', sa.String(255), nullable=False),
        sa.Column('website_url', sa.String(500), nullable=True),
        sa.Column('client_ip', sa.String(45), nullable=False),
        sa.Column('recommended_plan', sa.String(20), nullable=True),
        sa.Column('industry', sa.String(100), nullable=True),
        sa.Column('company_size', sa.String(50), nullable=True),
        sa.Column('thumbs_up', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('discover_logs')
