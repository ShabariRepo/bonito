"""add github app tables

Revision ID: 030_add_github_app_tables
Revises: cfc22bba5dd4
Create Date: 2026-03-17 06:50:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '030_add_github_app_tables'
down_revision: Union[str, None] = 'cfc22bba5dd4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── GitHub App Installations ──
    op.create_table(
        'github_app_installations',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),

        # GitHub identifiers
        sa.Column('installation_id', sa.BigInteger, nullable=False, unique=True),
        sa.Column('github_account_login', sa.String(255), nullable=False),
        sa.Column('github_account_id', sa.BigInteger, nullable=False),
        sa.Column('github_account_type', sa.String(50), nullable=False, server_default='User'),

        # Link to Bonito org (optional)
        sa.Column('org_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True),

        # Subscription tier
        sa.Column('tier', sa.String(50), nullable=False, server_default='free'),

        # Status
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('suspended_at', sa.DateTime(timezone=True), nullable=True),

        # Metadata
        sa.Column('target_type', sa.String(50), nullable=False, server_default='all'),
        sa.Column('permissions', sa.Text, nullable=True),
        sa.Column('events', sa.Text, nullable=True),

        # Timestamps
        sa.Column('installed_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )

    # Index for quick lookup by installation_id (also has unique constraint)
    op.create_index('ix_github_installations_installation_id',
                    'github_app_installations', ['installation_id'])
    op.create_index('ix_github_installations_org_id',
                    'github_app_installations', ['org_id'])

    # ── GitHub Review Usage ──
    op.create_table(
        'github_review_usage',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),

        sa.Column('installation_id', sa.BigInteger, nullable=False),
        sa.Column('installation_ref', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('github_app_installations.id', ondelete='CASCADE'), nullable=False),

        # PR identification
        sa.Column('repo_full_name', sa.String(500), nullable=False),
        sa.Column('pr_number', sa.Integer, nullable=False),
        sa.Column('pr_title', sa.String(500), nullable=True),
        sa.Column('pr_author', sa.String(255), nullable=True),
        sa.Column('commit_sha', sa.String(40), nullable=True),

        # Review details
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('comment_id', sa.BigInteger, nullable=True),
        sa.Column('review_summary', sa.Text, nullable=True),

        # Billing period
        sa.Column('billing_period', sa.String(7), nullable=False),

        # Error tracking
        sa.Column('error_message', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Indexes for usage queries
    op.create_index('ix_github_review_usage_installation_id',
                    'github_review_usage', ['installation_id'])
    op.create_index('ix_github_review_usage_billing_period',
                    'github_review_usage', ['installation_id', 'billing_period'])
    op.create_index('ix_github_review_usage_repo_pr',
                    'github_review_usage', ['repo_full_name', 'pr_number'])


def downgrade() -> None:
    op.drop_table('github_review_usage')
    op.drop_table('github_app_installations')
