import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, DateTime, Text, ForeignKey, Numeric, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active, paused, archived
    
    # Budget tracking
    budget_monthly: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=10, scale=2), nullable=True)  # monthly spend cap in USD
    budget_spent: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2), nullable=False, default=0)
    
    # Configuration
    settings: Mapped[dict] = mapped_column(JSON, default=dict)  # project-level settings
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agents = relationship("Agent", back_populates="project")
    agent_groups = relationship("AgentGroup", back_populates="project")
    connections = relationship("AgentConnection", back_populates="project")