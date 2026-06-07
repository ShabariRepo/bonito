"""Add origami_messages table for chat history.

Origami's billing + audit tables (origami_turn_log, origami_audit_log)
don't carry the actual chat content — they were designed for metering
and per-action forensics. This table stores the user-visible chat
exchange so users can view / download their past conversations.

One row per chat message:
- user prompts
- assistant replies (final text the user sees, including synthesized
  fallback summaries when the model went silent after a tool)
- plan cards (stored as a JSON-serialized PlanCard in content + metadata)

Tool execution events are NOT stored here — they live in
origami_audit_log. Use the join via conversation_id / session_id when
you want both views.

Revision ID: 048_origami_messages
Revises: 047_origami_project
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "048_origami_messages"
down_revision = "047_origami_project"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "origami_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("conversation_id", sa.String(255), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "role",
            sa.String(20),
            nullable=False,
        ),
        # user | assistant | plan | system
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "extra_metadata",
            postgresql.JSONB,
            nullable=True,
        ),
        sa.Column("model_used", sa.String(255), nullable=True),
        sa.Column("synthesized", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_origami_messages_org_conversation",
        "origami_messages",
        ["org_id", "conversation_id", "created_at"],
    )
    op.create_index(
        "ix_origami_messages_user_time",
        "origami_messages",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_origami_messages_conv",
        "origami_messages",
        ["conversation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_origami_messages_conv", table_name="origami_messages")
    op.drop_index("ix_origami_messages_user_time", table_name="origami_messages")
    op.drop_index("ix_origami_messages_org_conversation", table_name="origami_messages")
    op.drop_table("origami_messages")
