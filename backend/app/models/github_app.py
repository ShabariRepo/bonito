"""
GitHub App Models

Tables for tracking GitHub App installations and review usage.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class GitHubAppInstallation(Base):
    """Tracks each GitHub App installation (one per GitHub account/org)."""
    __tablename__ = "github_app_installations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # GitHub identifiers
    installation_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    github_account_login: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "octocat" or "my-org"
    github_account_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    github_account_type: Mapped[str] = mapped_column(String(50), nullable=False, default="User")  # "User" or "Organization"

    # Link to Bonito org (optional — set after OAuth callback)
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )

    # Subscription tier for this installation (independent of Bonito org)
    tier: Mapped[str] = mapped_column(String(50), nullable=False, default="free")  # "free" | "pro" | "enterprise"

    # Review persona (default, gilfoyle, dinesh, richard, jared, erlich)
    review_persona: Mapped[str] = mapped_column(String(50), nullable=False, default="default")

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    suspended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata
    target_type: Mapped[str] = mapped_column(String(50), nullable=False, default="all")  # "all" or "selected" repos
    permissions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string of granted permissions
    events: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string of subscribed events

    # Timestamps
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization")
    reviews = relationship("GitHubReviewUsage", back_populates="installation", cascade="all, delete-orphan")


class GitHubReviewUsage(Base):
    """Tracks each code review performed, for usage metering and billing."""
    __tablename__ = "github_review_usage"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    installation_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    installation_ref: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("github_app_installations.id", ondelete="CASCADE"), nullable=False
    )

    # PR identification
    repo_full_name: Mapped[str] = mapped_column(String(500), nullable=False)  # "owner/repo"
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pr_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    pr_author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)

    # Review details
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    # "pending" | "in_progress" | "completed" | "failed" | "skipped_rate_limit"
    comment_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # GitHub comment ID
    review_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Brief summary of review

    # Billing period (YYYY-MM format for monthly grouping)
    billing_period: Mapped[str] = mapped_column(String(7), nullable=False)  # e.g. "2026-03"

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    installation = relationship("GitHubAppInstallation", back_populates="reviews")
    snapshots = relationship("CodeReviewSnapshot", back_populates="review", cascade="all, delete-orphan")
