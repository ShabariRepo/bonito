import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Boolean, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class OnboardingProgress(Base):
    __tablename__ = "onboarding_progress"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, unique=True)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    selected_providers: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    selected_iac_tool: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    provider_credentials_validated: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    step_timestamps: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
