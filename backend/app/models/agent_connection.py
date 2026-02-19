import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AgentConnection(Base):
    __tablename__ = "agent_connections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    source_agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    target_agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    
    # Connection properties
    connection_type: Mapped[str] = mapped_column(String(30), nullable=False)  # "handoff", "escalation", "data_feed", "trigger"
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    condition: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # when to activate this connection
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="connections")
    source_agent = relationship("Agent", foreign_keys=[source_agent_id], back_populates="source_connections")
    target_agent = relationship("Agent", foreign_keys=[target_agent_id], back_populates="target_connections")