"""add org secrets table

Revision ID: 034_add_org_secrets_table
Revises: 033_update_copilot_system_prompt
Create Date: 2026-04-04 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '034_add_org_secrets_table'
down_revision: Union[str, None] = '033_update_copilot_system_prompt'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Org Secrets Store ──
    op.create_table(
        'org_secrets',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),

        # Org reference
        sa.Column('org_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id', ondelete='CASCADE'),
                  nullable=False),

        # Secret metadata (values stored in Vault)
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('vault_ref', sa.String(512), nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Indexes
    op.create_index('ix_org_secrets_org_id', 'org_secrets', ['org_id'])
    op.create_index('uq_org_secrets_org_name', 'org_secrets', ['org_id', 'name'], unique=True)


def downgrade() -> None:
    op.drop_index('uq_org_secrets_org_name', table_name='org_secrets')
    op.drop_index('ix_org_secrets_org_id', table_name='org_secrets')
    op.drop_table('org_secrets')
