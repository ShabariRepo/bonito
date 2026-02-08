import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Model(Base):
    __tablename__ = "models"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cloud_providers.id"), nullable=False)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict)
    pricing_info: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    provider = relationship("CloudProvider", back_populates="models")
    deployments = relationship("Deployment", back_populates="model")
