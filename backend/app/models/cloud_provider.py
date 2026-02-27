import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Text, Boolean, BigInteger, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CloudProvider(Base):
    __tablename__ = "cloud_providers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False)  # aws, azure, gcp, openai, anthropic, groq
    credentials_encrypted: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, active, error
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Managed inference fields
    is_managed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    managed_usage_tokens: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    managed_usage_cost: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0, server_default="0")

    organization = relationship("Organization", back_populates="cloud_providers")
    models = relationship("Model", back_populates="provider", passive_deletes=True)
    deployments = relationship("Deployment", back_populates="provider", passive_deletes=True)
