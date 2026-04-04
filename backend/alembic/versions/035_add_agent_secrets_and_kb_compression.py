"""add agent secrets and kb compression

Revision ID: 035_add_agent_secrets_and_kb_compression
Revises: 034_add_org_secrets_table
Create Date: 2026-04-04 00:01:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '035_add_agent_secrets_and_kb_compression'
down_revision: Union[str, None] = '034_add_org_secrets_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add secrets column to agents table
    # Stores list of secret names this agent can access at runtime
    op.add_column('agents', sa.Column('secrets', sa.JSON, nullable=True, server_default=None))

    # Add compression_method column to knowledge_bases table
    # null/None = off, "scalar-8bit", "polar-4bit", "polar-8bit"
    op.add_column('knowledge_bases', sa.Column('compression_method', sa.String(50), nullable=True, server_default=None))


def downgrade() -> None:
    op.drop_column('agents', 'secrets')
    op.drop_column('knowledge_bases', 'compression_method')
