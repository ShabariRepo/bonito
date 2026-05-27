"""Add access_tokens table for PATs and project tokens.

Revision ID: 044_add_access_tokens
Revises: 043_add_agent_autoscaling
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "044_add_access_tokens"
down_revision = "043_add_agent_autoscaling"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "access_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("token_type", sa.String(20), nullable=False),  # "personal" or "project"
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("token_prefix", sa.String(20), nullable=False),
        sa.Column("scopes", postgresql.JSON, nullable=True),
        sa.Column("rate_limit", sa.Integer, nullable=False, server_default="120"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_ip", sa.String(45), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_access_tokens_org_id", "access_tokens", ["org_id"])
    op.create_index("ix_access_tokens_user_id", "access_tokens", ["user_id"])
    op.create_index("ix_access_tokens_project_id", "access_tokens", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_access_tokens_project_id")
    op.drop_index("ix_access_tokens_user_id")
    op.drop_index("ix_access_tokens_org_id")
    op.drop_table("access_tokens")
