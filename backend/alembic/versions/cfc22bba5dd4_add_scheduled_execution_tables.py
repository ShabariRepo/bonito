"""add_scheduled_execution_tables

Revision ID: cfc22bba5dd4
Revises: 40771788af6d
Create Date: 2026-03-09 11:31:11.335453
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'cfc22bba5dd4'
down_revision: Union[str, None] = '40771788af6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create agent_schedules table for cron-like scheduled executions
    op.create_table(
        'agent_schedules',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('agent_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('org_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('cron_expression', sa.String(100), nullable=False),  # Standard cron format
        sa.Column('task_prompt', sa.Text, nullable=False),  # The message/prompt to send to agent
        sa.Column('output_config', sa.JSON, nullable=False, server_default='{}'),  # Webhook, email, Slack config
        sa.Column('enabled', sa.Boolean, nullable=False, default=True),
        sa.Column('timezone', sa.String(50), nullable=False, default='UTC'),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('run_count', sa.Integer, nullable=False, default=0),
        sa.Column('failure_count', sa.Integer, nullable=False, default=0),
        sa.Column('max_retries', sa.Integer, nullable=False, default=3),
        sa.Column('retry_delay_minutes', sa.Integer, nullable=False, default=5),
        sa.Column('timeout_minutes', sa.Integer, nullable=False, default=10),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create scheduled_executions table for tracking individual runs
    op.create_table(
        'scheduled_executions',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('schedule_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_schedules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_sessions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('org_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),  # 'pending', 'running', 'completed', 'failed', 'timeout'
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result_content', sa.Text, nullable=True),  # Agent's response
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('tokens_used', sa.Integer, nullable=True),
        sa.Column('cost', sa.Numeric(10, 6), nullable=True),
        sa.Column('output_delivered', sa.Boolean, nullable=False, default=False),
        sa.Column('output_log', sa.JSON, nullable=True),  # Log of output delivery attempts
        sa.Column('retry_count', sa.Integer, nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Add indexes for performance
    op.create_index('idx_agent_schedules_agent_id', 'agent_schedules', ['agent_id'])
    op.create_index('idx_agent_schedules_next_run_at', 'agent_schedules', ['next_run_at'])
    op.create_index('idx_agent_schedules_enabled', 'agent_schedules', ['enabled'])
    
    op.create_index('idx_scheduled_executions_schedule_id', 'scheduled_executions', ['schedule_id'])
    op.create_index('idx_scheduled_executions_status', 'scheduled_executions', ['status'])
    op.create_index('idx_scheduled_executions_scheduled_at', 'scheduled_executions', ['scheduled_at'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_scheduled_executions_scheduled_at', 'scheduled_executions')
    op.drop_index('idx_scheduled_executions_status', 'scheduled_executions')
    op.drop_index('idx_scheduled_executions_schedule_id', 'scheduled_executions')
    
    op.drop_index('idx_agent_schedules_enabled', 'agent_schedules')
    op.drop_index('idx_agent_schedules_next_run_at', 'agent_schedules')
    op.drop_index('idx_agent_schedules_agent_id', 'agent_schedules')
    
    # Drop tables
    op.drop_table('scheduled_executions')
    op.drop_table('agent_schedules')
