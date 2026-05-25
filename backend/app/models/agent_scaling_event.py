import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Integer, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class AgentScalingEvent(Base):
    __tablename__ = "agent_scaling_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)  # scale_up, scale_down
    previous_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    new_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    replica_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trigger_utilization: Mapped[float] = mapped_column(Numeric(precision=5, scale=4), nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
