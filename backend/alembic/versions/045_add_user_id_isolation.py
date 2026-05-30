"""Add user_id isolation for agent sessions and patient profiles.

Revision ID: 045_add_user_id_isolation
Revises: 044_add_access_tokens
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "045_add_user_id_isolation"
down_revision = "044_add_access_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add user_id to agent_sessions (nullable initially for backfill)
    op.add_column(
        "agent_sessions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True)
    )

    # Add FK constraint after column exists
    op.create_foreign_key(
        "fk_agent_sessions_user_id",
        "agent_sessions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE"
    )

    # Add index for query performance
    op.create_index(
        "ix_agent_sessions_user_id",
        "agent_sessions",
        ["user_id"]
    )

    # 2. Add user_id to agent_messages (nullable initially for backfill)
    op.add_column(
        "agent_messages",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True)
    )

    op.create_foreign_key(
        "fk_agent_messages_user_id",
        "agent_messages",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE"
    )

    op.create_index(
        "ix_agent_messages_user_id",
        "agent_messages",
        ["user_id"]
    )

    # 3. Add user_id to agent_memories (if table exists)
    # Check if agent_memories table exists first
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()

    if "agent_memories" in tables:
        op.add_column(
            "agent_memories",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True)
        )

        op.create_foreign_key(
            "fk_agent_memories_user_id",
            "agent_memories",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE"
        )

        op.create_index(
            "ix_agent_memories_user_id",
            "agent_memories",
            ["user_id"]
        )

    # 4. Create patient_profiles table (for OuchGPT)
    op.create_table(
        "patient_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("orchestrator_agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_kb_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("injury_type", sa.String(100), nullable=False),  # achilles, acl, rotator_cuff, etc.
        sa.Column("surgery_date", sa.Date, nullable=False),
        sa.Column("surgeon_name", sa.String(255), nullable=True),
        sa.Column("pt_clinic", sa.String(255), nullable=True),
        sa.Column("recovery_phase", sa.Integer, nullable=True),  # 1, 2, 3, etc. (auto-calculated)
        sa.Column("days_since_surgery", sa.Integer, nullable=True),  # auto-calculated
        sa.Column("metadata", postgresql.JSON, nullable=True),  # additional patient data
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Add indexes
    op.create_index("ix_patient_profiles_org_id", "patient_profiles", ["org_id"])
    op.create_index("ix_patient_profiles_user_id", "patient_profiles", ["user_id"])
    op.create_index("ix_patient_profiles_orchestrator_agent_id", "patient_profiles", ["orchestrator_agent_id"])
    op.create_index("ix_patient_profiles_injury_type", "patient_profiles", ["injury_type"])

    # Note: orchestrator_agent_id and patient_kb_id FKs are not enforced
    # because agents and KBs may be in different databases or managed externally
    # (they are Bonito platform resources, not app-level resources)


def downgrade() -> None:
    # Drop patient_profiles table
    op.drop_index("ix_patient_profiles_injury_type")
    op.drop_index("ix_patient_profiles_orchestrator_agent_id")
    op.drop_index("ix_patient_profiles_user_id")
    op.drop_index("ix_patient_profiles_org_id")
    op.drop_table("patient_profiles")

    # Remove user_id from agent_memories (if it was added)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()

    if "agent_memories" in tables:
        op.drop_index("ix_agent_memories_user_id")
        op.drop_constraint("fk_agent_memories_user_id", "agent_memories", type_="foreignkey")
        op.drop_column("agent_memories", "user_id")

    # Remove user_id from agent_messages
    op.drop_index("ix_agent_messages_user_id")
    op.drop_constraint("fk_agent_messages_user_id", "agent_messages", type_="foreignkey")
    op.drop_column("agent_messages", "user_id")

    # Remove user_id from agent_sessions
    op.drop_index("ix_agent_sessions_user_id")
    op.drop_constraint("fk_agent_sessions_user_id", "agent_sessions", type_="foreignkey")
    op.drop_column("agent_sessions", "user_id")
