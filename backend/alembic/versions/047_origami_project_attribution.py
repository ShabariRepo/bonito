"""Add project_id to origami_audit_log + origami_turn_log.

Lets us answer "which project was this Origami activity scoped to?" — the
customer org has many projects (one per tenant/team), so per-org isn't
granular enough for usage analytics or compliance investigations.

Both columns are nullable: Origami activity outside any specific project
context (general onboarding, "what's my org tier?") doesn't have one.

Revision ID: 047_origami_project
Revises: 046_origami_logs
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "047_origami_project"
down_revision = "046_origami_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # origami_audit_log: project_id nullable FK
    op.add_column(
        "origami_audit_log",
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_origami_audit_project",
        "origami_audit_log",
        ["project_id", "created_at"],
    )

    # origami_turn_log: project_id nullable FK
    op.add_column(
        "origami_turn_log",
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_origami_turn_project_period",
        "origami_turn_log",
        ["project_id", "billing_period_month"],
    )


def downgrade() -> None:
    op.drop_index("ix_origami_turn_project_period", table_name="origami_turn_log")
    op.drop_column("origami_turn_log", "project_id")
    op.drop_index("ix_origami_audit_project", table_name="origami_audit_log")
    op.drop_column("origami_audit_log", "project_id")
