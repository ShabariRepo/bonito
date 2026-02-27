import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AgentMCPServer(Base):
    """MCP (Model Context Protocol) server configuration for a Bonobot agent.

    Each record represents one MCP server that an agent can connect to.
    The agent engine acts as an MCP client, connecting to these servers
    to discover and execute tools.
    """

    __tablename__ = "agent_mcp_servers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Transport: "stdio" (local subprocess) or "http" (remote HTTP/SSE)
    transport_type: Mapped[str] = mapped_column(String(10), nullable=False, default="stdio")
    
    # Transport-specific configuration
    # stdio: {"command": "npx", "args": [...], "env": {...}, "cwd": "/path"}
    # http:  {"url": "https://...", "headers": {...}}
    endpoint_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    # Authentication configuration
    # {"type": "none"} | {"type": "bearer_token", "token": "..."} | {"type": "api_key", "header": "...", "key": "..."}
    auth_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {"type": "none"})
    
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Cached tool definitions from last successful tools/list call
    discovered_tools: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    # Last successful connection timestamp
    last_connected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="mcp_servers")
