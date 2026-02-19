import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Integer, JSON, Numeric, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    session_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)  # like "agent:{agent_id}:{session_id}"
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # auto-generated from first message
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active, compacted, archived
    
    # Statistics
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=4), nullable=False, default=0)
    
    # Configuration
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Timestamps
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="sessions")
    messages = relationship("AgentMessage", back_populates="session", order_by="AgentMessage.sequence")