import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Subscription fields
    subscription_tier: Mapped[str] = mapped_column(String(50), nullable=False, default="free", server_default="free")
    subscription_status: Mapped[str] = mapped_column(String(50), nullable=False, default="active", server_default="active")
    subscription_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Bonobot add-on
    bonobot_plan: Mapped[str] = mapped_column(String(50), nullable=False, default="none", server_default="none")
    bonobot_agent_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    cloud_providers = relationship("CloudProvider", back_populates="organization")
    deployments = relationship("Deployment", back_populates="organization")
