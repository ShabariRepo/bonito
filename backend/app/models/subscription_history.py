import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class SubscriptionHistory(Base):
    __tablename__ = "subscription_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    # Change details
    previous_tier: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_tier: Mapped[str] = mapped_column(String(50), nullable=False)
    previous_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Bonobot changes
    previous_bonobot_plan: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_bonobot_plan: Mapped[str] = mapped_column(String(50), nullable=False, default="none")
    previous_bonobot_agent_limit: Mapped[Optional[int]] = mapped_column(nullable=True)
    new_bonobot_agent_limit: Mapped[int] = mapped_column(nullable=False, default=0)
    
    # Metadata
    changed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    organization = relationship("Organization")
    changed_by = relationship("User")