import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Float, Date
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class CostRecord(Base):
    __tablename__ = "cost_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=True)
    cost_amount: Mapped[float] = mapped_column(Float, nullable=False)
    tokens_used: Mapped[int] = mapped_column(nullable=False, default=0)
    requests_count: Mapped[int] = mapped_column(nullable=False, default=0)
    record_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
