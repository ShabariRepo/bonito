import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, DateTime, Text, ForeignKey, Numeric, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AgentGroup(Base):
    __tablename__ = "agent_groups"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Knowledge Base Isolation
    knowledge_base_ids: Mapped[list] = mapped_column(JSON, default=list)  # Array of KB UUIDs for this group
    
    # Group-level Settings  
    budget_limit: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=10, scale=2), nullable=True)
    model_allowlist: Mapped[list] = mapped_column(JSON, default=list)  # Models this group can use
    tool_policy: Mapped[dict] = mapped_column(JSON, default=lambda: {"mode": "inherit", "allowed": [], "denied": []})
    
    # Visual Grouping (for React Flow canvas)
    canvas_position: Mapped[Optional[dict]] = mapped_column(JSON, default=lambda: {"x": 0, "y": 0})
    canvas_style: Mapped[Optional[dict]] = mapped_column(JSON, default=lambda: {"backgroundColor": "#f0f0f0", "borderColor": "#ccc"})
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="agent_groups")
    agents = relationship("Agent", back_populates="group")