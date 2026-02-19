import uuid
from datetime import datetime
from typing import Optional
from enum import Enum

from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ScopeType(str, Enum):
    ORG = "org"
    PROJECT = "project"
    GROUP = "group"


class RoleAssignment(Base):
    __tablename__ = "role_assignments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    # Scope defines WHERE this role applies
    scope_type: Mapped[ScopeType] = mapped_column(SQLEnum(ScopeType), nullable=False)
    scope_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)  # NULL for org-level, project_id for project-level, group_id for group-level
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="role_assignments")
    role = relationship("Role", back_populates="assignments")