import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Text, ForeignKey, Integer, Boolean, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AgentApprovalAction(Base):
    __tablename__ = "agent_approval_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False)
    message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_messages.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    # Action details
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'send_email', 'modify_data', 'external_api', 'file_operation', etc.
    action_description: Mapped[str] = mapped_column(Text, nullable=False)  # Human-readable description
    action_payload: Mapped[dict] = mapped_column(JSON, nullable=False)  # The actual parameters for the action
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default='medium')  # 'low', 'medium', 'high', 'critical'
    
    # Approval workflow
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='pending')  # 'pending', 'approved', 'rejected', 'expired', 'executed'
    requested_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # User who initiated the conversation
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timing
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)  # Auto-reject after this time
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Execution results
    execution_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Result of executing the action
    execution_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agent = relationship("Agent")
    session = relationship("AgentSession")
    message = relationship("AgentMessage")
    requester = relationship("User", foreign_keys=[requested_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class AgentApprovalConfig(Base):
    __tablename__ = "agent_approval_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    # Configuration
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_approve_conditions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Conditions for auto-approval
    timeout_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)  # Hours before auto-reject
    required_approvers: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # Number of approvals needed
    risk_assessment_rules: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Rules for determining risk level
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="approval_configs")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('agent_id', 'action_type', name='uq_agent_approval_config'),
    )