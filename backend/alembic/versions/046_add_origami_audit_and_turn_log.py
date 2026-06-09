"""Add origami_audit_log and origami_turn_log tables.

Two tables, two purposes:

- origami_audit_log: per-tool-call audit record. One row every time a tool
  fires inside an Origami turn. For forensics, compliance, abuse
  investigation. Append-only by app convention.

- origami_turn_log: per-turn billing record. One row per user-visible
  chat exchange. Carries summed cost, token counts, tool-call count, the
  user's org_id (used for billing) and the og_token_id used. This is
  what powers the per-org Origami usage page and tier quota enforcement.

Both are independent of gateway_requests. A single Origami turn fans out
into multiple gateway_requests rows (each LLM call) — these tables give us
the turn boundary so we can count "Origami turns" against the tier cap.

Revision ID: 046_origami_logs
Revises: 045_add_user_id_isolation
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "046_origami_logs"
down_revision = "045_add_user_id_isolation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─────────────────────────── origami_audit_log ───────────────────────────
    op.create_table(
        "origami_audit_log",
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
            "og_token_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("access_tokens.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_card_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("intent_summary", sa.Text(), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("tool_params", postgresql.JSONB, nullable=False),
        sa.Column("tier_at_time", sa.String(50), nullable=False),
        sa.Column("confirmation", sa.String(50), nullable=False),  # auto | user_clicked | upgrade_then_auto
        sa.Column("status", sa.String(50), nullable=False),  # success | failed | partial
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_origami_audit_org_time",
        "origami_audit_log",
        ["org_id", "created_at"],
    )
    op.create_index(
        "ix_origami_audit_user",
        "origami_audit_log",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_origami_audit_token",
        "origami_audit_log",
        ["og_token_id"],
    )

    # ─────────────────────────── origami_turn_log ───────────────────────────
    op.create_table(
        "origami_turn_log",
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
            "og_token_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("access_tokens.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", sa.String(255), nullable=True),
        sa.Column("user_message_preview", sa.String(500), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "cost_usd",
            sa.Numeric(12, 6),
            nullable=False,
            server_default="0",
        ),
        sa.Column("tool_calls_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model_used", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),  # success | failed | over_quota
        sa.Column("finish_reason", sa.String(50), nullable=True),
        sa.Column(
            "billing_period_month",
            sa.String(7),  # 'YYYY-MM'
            nullable=False,
        ),
        sa.Column("tier_at_time", sa.String(50), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "gateway_request_ids",
            postgresql.JSONB,
            nullable=True,
        ),  # ids of constituent gateway_requests rows for traceability
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Index for the hot query: "how many turns has this org used this month"
    op.create_index(
        "ix_origami_turn_org_period",
        "origami_turn_log",
        ["org_id", "billing_period_month"],
    )
    op.create_index(
        "ix_origami_turn_user_time",
        "origami_turn_log",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_origami_turn_token",
        "origami_turn_log",
        ["og_token_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_origami_turn_token", table_name="origami_turn_log")
    op.drop_index("ix_origami_turn_user_time", table_name="origami_turn_log")
    op.drop_index("ix_origami_turn_org_period", table_name="origami_turn_log")
    op.drop_table("origami_turn_log")

    op.drop_index("ix_origami_audit_token", table_name="origami_audit_log")
    op.drop_index("ix_origami_audit_user", table_name="origami_audit_log")
    op.drop_index("ix_origami_audit_org_time", table_name="origami_audit_log")
    op.drop_table("origami_audit_log")
