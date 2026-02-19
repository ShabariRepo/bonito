"""Add SSO/SAML configuration table

Revision ID: 019_add_sso_config
Revises: 018_fix_kb_embed
Create Date: 2026-02-19

Adds sso_configs table for per-organization SAML SSO settings.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "019_add_sso_config"
down_revision = "018_fix_kb_embed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sso_configs",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("provider_type", sa.String(50), nullable=False, server_default="custom"),
        sa.Column("idp_metadata_url", sa.String(1000), nullable=True),
        sa.Column("idp_sso_url", sa.String(1000), nullable=True),
        sa.Column("idp_entity_id", sa.String(500), nullable=True),
        sa.Column("idp_certificate", sa.Text(), nullable=True),
        sa.Column("sp_entity_id", sa.String(500), nullable=True),
        sa.Column("sp_acs_url", sa.String(1000), nullable=True),
        sa.Column("attribute_mapping", sa.JSON(), nullable=True),
        sa.Column("role_mapping", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("enforced", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("breakglass_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # Index for quick lookup by org
    op.create_index("ix_sso_configs_org_id", "sso_configs", ["org_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_sso_configs_org_id", table_name="sso_configs")
    op.drop_table("sso_configs")
