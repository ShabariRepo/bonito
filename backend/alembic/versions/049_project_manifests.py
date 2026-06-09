"""project_manifests — store deleted project structures for skeleton restore

Revision ID: 049_project_manifests
Revises: 048_origami_messages
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = "049_project_manifests"
down_revision = "048_origami_messages"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "project_manifests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("manifest", JSONB, nullable=False),
        sa.Column("deleted_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("restored_to_project_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_project_manifests_org_id", "project_manifests", ["org_id"])
    op.create_index("ix_project_manifests_deleted_at", "project_manifests", ["deleted_at"])


def downgrade():
    op.drop_index("ix_project_manifests_deleted_at", table_name="project_manifests")
    op.drop_index("ix_project_manifests_org_id", table_name="project_manifests")
    op.drop_table("project_manifests")
