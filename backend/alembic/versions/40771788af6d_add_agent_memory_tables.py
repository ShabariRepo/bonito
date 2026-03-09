"""add_agent_memory_tables

Revision ID: 40771788af6d
Revises: 029_add_model_status_column
Create Date: 2026-03-09 11:30:34.572979
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '40771788af6d'
down_revision: Union[str, None] = '029_add_model_status_column'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create agent_memories table for storing persistent memories with vector search
    op.create_table(
        'agent_memories',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('agent_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('org_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('memory_type', sa.String(50), nullable=False),  # 'fact', 'pattern', 'interaction', 'preference', 'context'
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('metadata', sa.JSON, nullable=False, server_default='{}'),
        sa.Column('importance_score', sa.Float, nullable=False, default=1.0),
        sa.Column('access_count', sa.Integer, nullable=False, default=0),
        sa.Column('embedding', sa.Text, nullable=True),  # For vector search - will store as text and cast to vector
        sa.Column('source_session_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_sessions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_message_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_messages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Add indexes for performance
    op.create_index('idx_agent_memories_agent_id', 'agent_memories', ['agent_id'])
    op.create_index('idx_agent_memories_project_id', 'agent_memories', ['project_id'])
    op.create_index('idx_agent_memories_memory_type', 'agent_memories', ['memory_type'])
    op.create_index('idx_agent_memories_importance', 'agent_memories', ['importance_score'])
    op.create_index('idx_agent_memories_created_at', 'agent_memories', ['created_at'])
    
    # Add vector index for similarity search (requires pgvector extension)
    # First create the vector column type, then add the index
    op.execute("ALTER TABLE agent_memories ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector")
    op.execute("CREATE INDEX IF NOT EXISTS idx_agent_memories_embedding ON agent_memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_agent_memories_embedding', 'agent_memories')
    op.drop_index('idx_agent_memories_created_at', 'agent_memories')
    op.drop_index('idx_agent_memories_importance', 'agent_memories')
    op.drop_index('idx_agent_memories_memory_type', 'agent_memories')
    op.drop_index('idx_agent_memories_project_id', 'agent_memories')
    op.drop_index('idx_agent_memories_agent_id', 'agent_memories')
    
    # Drop table
    op.drop_table('agent_memories')
