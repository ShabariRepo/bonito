"""Add Bonobot agent framework tables

Revision ID: 020_add_bonobot_tables
Revises: 019_add_sso_config
Create Date: 2026-02-19

Adds the core Bonobot tables for enterprise AI agents:
- projects: Agent containers
- agents: Individual AI agents with OpenClaw-style configuration  
- agent_sessions: Isolated conversation sessions per agent
- agent_messages: Message history (system, user, assistant, tool)
- agent_connections: Visual graph connections between agents
- agent_triggers: Event triggers for agent activation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "020_add_bonobot_tables"
down_revision = "019_add_sso_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Projects table
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("budget_monthly", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("budget_spent", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
        sa.Column("settings", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # Agents table
    op.create_table(
        "agents",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("model_id", sa.String(100), nullable=False, server_default="auto"),
        sa.Column("model_config", sa.JSON(), nullable=True),
        sa.Column("knowledge_base_ids", sa.JSON(), nullable=True),
        sa.Column("tool_policy", sa.JSON(), nullable=True),
        sa.Column("max_turns", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("compaction_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_runs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Numeric(precision=10, scale=4), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # Agent Sessions table
    op.create_table(
        "agent_sessions",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_key", sa.String(255), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Numeric(precision=10, scale=4), nullable=False, server_default="0"),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # Agent Messages table
    op.create_table(
        "agent_messages",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("tool_calls", sa.JSON(), nullable=True),
        sa.Column("tool_call_id", sa.String(255), nullable=True),
        sa.Column("tool_name", sa.String(100), nullable=True),
        sa.Column("is_compaction_summary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # Agent Connections table
    op.create_table(
        "agent_connections",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connection_type", sa.String(30), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("condition", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # Agent Triggers table
    op.create_table(
        "agent_triggers",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trigger_type", sa.String(30), nullable=False),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_fired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add indexes for performance
    op.create_index("ix_projects_org_id", "projects", ["org_id"])
    op.create_index("ix_agents_project_id", "agents", ["project_id"])
    op.create_index("ix_agents_org_id", "agents", ["org_id"])
    op.create_index("ix_agent_sessions_agent_id", "agent_sessions", ["agent_id"])
    op.create_index("ix_agent_sessions_org_id", "agent_sessions", ["org_id"])
    op.create_index("ix_agent_messages_session_id", "agent_messages", ["session_id"])
    op.create_index("ix_agent_messages_sequence", "agent_messages", ["session_id", "sequence"])
    op.create_index("ix_agent_connections_project_id", "agent_connections", ["project_id"])
    op.create_index("ix_agent_connections_source_agent_id", "agent_connections", ["source_agent_id"])
    op.create_index("ix_agent_connections_target_agent_id", "agent_connections", ["target_agent_id"])
    op.create_index("ix_agent_triggers_agent_id", "agent_triggers", ["agent_id"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_agent_triggers_agent_id", table_name="agent_triggers")
    op.drop_index("ix_agent_connections_target_agent_id", table_name="agent_connections")
    op.drop_index("ix_agent_connections_source_agent_id", table_name="agent_connections")
    op.drop_index("ix_agent_connections_project_id", table_name="agent_connections")
    op.drop_index("ix_agent_messages_sequence", table_name="agent_messages")
    op.drop_index("ix_agent_messages_session_id", table_name="agent_messages")
    op.drop_index("ix_agent_sessions_org_id", table_name="agent_sessions")
    op.drop_index("ix_agent_sessions_agent_id", table_name="agent_sessions")
    op.drop_index("ix_agents_org_id", table_name="agents")
    op.drop_index("ix_agents_project_id", table_name="agents")
    op.drop_index("ix_projects_org_id", table_name="projects")

    # Drop tables in reverse order of dependencies
    op.drop_table("agent_triggers")
    op.drop_table("agent_connections")
    op.drop_table("agent_messages")
    op.drop_table("agent_sessions")
    op.drop_table("agents")
    op.drop_table("projects")