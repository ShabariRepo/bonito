import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Float, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # cost_alert, compliance_alert, model_deprecation, digest
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # budget_threshold, compliance_violation, model_deprecation
    threshold: Mapped[float] = mapped_column(Float, nullable=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="in_app")  # email, webhook, in_app
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    weekly_digest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cost_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    compliance_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    model_updates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
