import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_managed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # Built-in roles cannot be deleted
    
    # Permissions as JSON array of permission objects
    # Example: [
    #   {"action": "manage_agents", "resource_type": "group", "resource_ids": ["group-uuid"]},
    #   {"action": "view_sessions", "resource_type": "project", "resource_ids": ["*"]}
    # ]
    permissions: Mapped[list] = mapped_column(JSON, default=list)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    assignments = relationship("RoleAssignment", back_populates="role")