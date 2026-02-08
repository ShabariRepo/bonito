"""Add onboarding_progress table

Revision ID: 007_onboarding
Revises: 006_add_hashed_password
Create Date: 2026-02-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "007_onboarding"
down_revision = "006_add_hashed_password"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "onboarding_progress",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("selected_providers", sa.JSON(), nullable=True),  # ["aws", "azure", "gcp"]
        sa.Column("selected_iac_tool", sa.String(50), nullable=True),  # terraform, pulumi, cloudformation, bicep, manual
        sa.Column("provider_credentials_validated", sa.JSON(), nullable=True),  # {"aws": true, "azure": false}
        sa.Column("step_timestamps", sa.JSON(), nullable=True),  # {"1": "2026-...", "2": "2026-..."}
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade():
    op.drop_table("onboarding_progress")
