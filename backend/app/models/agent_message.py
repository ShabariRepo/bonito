import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, DateTime, Text, ForeignKey, Integer, Boolean, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    # Message content
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "system", "user", "assistant", "tool"
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # For tool calls
    tool_calls: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # [{id, function: {name, arguments}}]
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # for role="tool" responses
    tool_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # For compaction
    is_compaction_summary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Metadata
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=10, scale=6), nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Ordering
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)  # ordering within session
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("AgentSession", back_populates="messages")