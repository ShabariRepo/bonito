"""add_approval_queue_tables

Revision ID: 0b1b3e3d1a88
Revises: cfc22bba5dd4
Create Date: 2026-03-09 11:31:37.868309
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '0b1b3e3d1a88'
down_revision: Union[str, None] = 'cfc22bba5dd4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create agent_approval_actions table for tracking actions that require approval
    op.create_table(
        'agent_approval_actions',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('agent_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('message_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_messages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('org_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_type', sa.String(50), nullable=False),  # 'send_email', 'modify_data', 'external_api', 'file_operation', etc.
        sa.Column('action_description', sa.Text, nullable=False),  # Human-readable description of what the agent wants to do
        sa.Column('action_payload', sa.JSON, nullable=False),  # The actual parameters for the action
        sa.Column('risk_level', sa.String(20), nullable=False, default='medium'),  # 'low', 'medium', 'high', 'critical'
        sa.Column('status', sa.String(20), nullable=False, default='pending'),  # 'pending', 'approved', 'rejected', 'expired', 'executed'
        sa.Column('requested_by', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),  # User who initiated the conversation
        sa.Column('reviewed_by', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('review_notes', sa.Text, nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),  # Auto-reject after this time
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_result', sa.JSON, nullable=True),  # Result of executing the action
        sa.Column('execution_error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create agent_approval_config table for configuring which actions require approval per agent
    op.create_table(
        'agent_approval_configs',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('agent_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('org_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_type', sa.String(50), nullable=False),
        sa.Column('requires_approval', sa.Boolean, nullable=False, default=True),
        sa.Column('auto_approve_conditions', sa.JSON, nullable=True),  # Conditions for auto-approval (e.g., amount limits)
        sa.Column('timeout_hours', sa.Integer, nullable=False, default=24),  # Hours before auto-reject
        sa.Column('required_approvers', sa.Integer, nullable=False, default=1),  # Number of approvals needed
        sa.Column('risk_assessment_rules', sa.JSON, nullable=True),  # Rules for determining risk level
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Add indexes for performance
    op.create_index('idx_agent_approval_actions_agent_id', 'agent_approval_actions', ['agent_id'])
    op.create_index('idx_agent_approval_actions_status', 'agent_approval_actions', ['status'])
    op.create_index('idx_agent_approval_actions_expires_at', 'agent_approval_actions', ['expires_at'])
    op.create_index('idx_agent_approval_actions_org_id', 'agent_approval_actions', ['org_id'])
    op.create_index('idx_agent_approval_actions_risk_level', 'agent_approval_actions', ['risk_level'])
    
    op.create_index('idx_agent_approval_configs_agent_id', 'agent_approval_configs', ['agent_id'])
    op.create_index('idx_agent_approval_configs_action_type', 'agent_approval_configs', ['action_type'])

    # Add unique constraint to prevent duplicate approval configs per agent+action_type
    op.create_unique_constraint('uq_agent_approval_config', 'agent_approval_configs', ['agent_id', 'action_type'])


def downgrade() -> None:
    # Drop unique constraint first
    op.drop_constraint('uq_agent_approval_config', 'agent_approval_configs', type_='unique')
    
    # Drop indexes
    op.drop_index('idx_agent_approval_configs_action_type', 'agent_approval_configs')
    op.drop_index('idx_agent_approval_configs_agent_id', 'agent_approval_configs')
    
    op.drop_index('idx_agent_approval_actions_risk_level', 'agent_approval_actions')
    op.drop_index('idx_agent_approval_actions_org_id', 'agent_approval_actions')
    op.drop_index('idx_agent_approval_actions_expires_at', 'agent_approval_actions')
    op.drop_index('idx_agent_approval_actions_status', 'agent_approval_actions')
    op.drop_index('idx_agent_approval_actions_agent_id', 'agent_approval_actions')
    
    # Drop tables
    op.drop_table('agent_approval_configs')
    op.drop_table('agent_approval_actions')
