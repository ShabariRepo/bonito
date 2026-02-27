"""Add agent_mcp_servers table for MCP integration.

Stores MCP (Model Context Protocol) server configurations per agent.
Each agent can connect to multiple MCP servers to discover and use
external tools via the MCP protocol.

Revision ID: 024_agent_mcp_servers
Revises: 023_cleanup_azure
Create Date: 2026-02-26
"""
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "024_agent_mcp_servers"
down_revision: Union[str, None] = "023_cleanup_azure"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_mcp_servers",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("transport_type", sa.String(length=10), nullable=False, server_default="stdio"),
        sa.Column("endpoint_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("auth_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{"type": "none"}'),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("discovered_tools", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_mcp_servers_agent_id", "agent_mcp_servers", ["agent_id"])
    op.create_index("ix_agent_mcp_servers_org_id", "agent_mcp_servers", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_mcp_servers_org_id", table_name="agent_mcp_servers")
    op.drop_index("ix_agent_mcp_servers_agent_id", table_name="agent_mcp_servers")
    op.drop_table("agent_mcp_servers")
