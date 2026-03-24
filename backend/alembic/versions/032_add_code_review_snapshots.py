"""add code review snapshots

Revision ID: 032_add_code_review_snapshots
Revises: 031_merge_heads
Create Date: 2026-03-24 19:25:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '032_add_code_review_snapshots'
down_revision: Union[str, None] = '031_merge_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Code Review Snapshots ──
    op.create_table(
        'code_review_snapshots',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),

        # Link to review
        sa.Column('review_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('github_review_usage.id', ondelete='CASCADE'), 
                  nullable=False),

        # Snapshot content
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),  # critical | warning | suggestion | info
        sa.Column('category', sa.String(50), nullable=False),  # security | performance | logic | architecture | style
        sa.Column('file_path', sa.String(1000), nullable=False),
        sa.Column('start_line', sa.Integer, nullable=True),
        sa.Column('end_line', sa.Integer, nullable=True),
        sa.Column('code_block', sa.Text, nullable=False),
        sa.Column('annotation', sa.Text, nullable=False),
        sa.Column('sort_order', sa.Integer, nullable=False, server_default=sa.text('0')),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    # Indexes for quick lookup
    op.create_index('ix_code_review_snapshots_review_id',
                    'code_review_snapshots', ['review_id'])
    op.create_index('ix_code_review_snapshots_severity_order',
                    'code_review_snapshots', ['review_id', 'sort_order'])

    # Add review_persona column to github_app_installations if it doesn't exist
    # This ensures backward compatibility
    try:
        op.add_column('github_app_installations', 
                      sa.Column('review_persona', sa.String(50), nullable=False, 
                               server_default='default'))
    except Exception:
        # Column might already exist, ignore the error
        pass


def downgrade() -> None:
    op.drop_table('code_review_snapshots')
    try:
        op.drop_column('github_app_installations', 'review_persona')
    except Exception:
        # Column might not exist or have constraints, ignore
        pass