import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, DateTime, Text, ForeignKey, Integer, Boolean, JSON, Numeric, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Agent configuration (OpenClaw-style)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)  # The agent's personality/instructions
    model_id: Mapped[str] = mapped_column(String(100), nullable=False, default="auto")  # model to use, or "auto" for smart routing
    model_config: Mapped[dict] = mapped_column(JSON, default=dict)  # temperature, max_tokens, etc.
    
    # Knowledge & Tools
    knowledge_base_ids: Mapped[list] = mapped_column(JSON, default=list)  # list of KB UUIDs this agent can access
    tool_policy: Mapped[dict] = mapped_column(JSON, default=lambda: {"mode": "default", "allowed": [], "denied": []})
    
    # Runtime settings
    max_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=25)  # max tool call loops per run
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    compaction_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active, paused, disabled
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Metrics
    total_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=4), nullable=False, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="agents")
    sessions = relationship("AgentSession", back_populates="agent")
    triggers = relationship("AgentTrigger", back_populates="agent")
    source_connections = relationship("AgentConnection", foreign_keys="[AgentConnection.source_agent_id]", back_populates="source_agent")
    target_connections = relationship("AgentConnection", foreign_keys="[AgentConnection.target_agent_id]", back_populates="target_agent")