"""
Code Review Snapshots Model

Stores extracted key code blocks from AI code reviews.
These are the most important snippets that developers should focus on.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CodeReviewSnapshot(Base):
    """
    Represents a key code block extracted from an AI code review.
    These are the critical snippets that matter most in a PR.
    """
    __tablename__ = "code_review_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    # Link to the review that generated this snapshot
    review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("github_review_usage.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )

    # Snapshot content
    title: Mapped[str] = mapped_column(String(500), nullable=False)  # e.g. "SQL injection in user lookup"
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # "critical" | "warning" | "suggestion" | "info"
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # "security" | "performance" | "logic" | "architecture" | "style"
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)  # path in repo
    start_line: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_line: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    code_block: Mapped[str] = mapped_column(Text, nullable=False)  # the actual code snippet
    annotation: Mapped[str] = mapped_column(Text, nullable=False)  # LLM's explanation of why this matters
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # display order (severity-based)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    review = relationship("GitHubReviewUsage", back_populates="snapshots")