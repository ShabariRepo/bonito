"""SOC2 audit hardening — nullable org_id, tamper-evident hash chain, indexes

Revision ID: 038_audit_soc2_hardening
Revises: 037_access_requests
Create Date: 2026-04-25 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '038_audit_soc2_hardening'
down_revision: Union[str, Sequence[str], None] = '037_access_requests'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make org_id nullable (auth failures have no org context)
    op.alter_column('audit_logs', 'org_id', existing_type=sa.UUID(), nullable=True)

    # Add tamper-evident hash chain columns
    op.add_column('audit_logs', sa.Column('prev_hash', sa.String(64), nullable=True))
    op.add_column('audit_logs', sa.Column('entry_hash', sa.String(64), nullable=False, server_default=''))

    # Performance indexes for SOC2 audit queries
    op.create_index('idx_audit_logs_org_created', 'audit_logs', ['org_id', 'created_at'])
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action', 'created_at'])
    op.create_index('idx_audit_logs_ip', 'audit_logs', ['ip_address', 'created_at'])


def downgrade() -> None:
    op.drop_index('idx_audit_logs_ip', table_name='audit_logs')
    op.drop_index('idx_audit_logs_action', table_name='audit_logs')
    op.drop_index('idx_audit_logs_org_created', table_name='audit_logs')
    op.drop_column('audit_logs', 'entry_hash')
    op.drop_column('audit_logs', 'prev_hash')
    op.alter_column('audit_logs', 'org_id', existing_type=sa.UUID(), nullable=False)
