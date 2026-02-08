"""Base types and abstract checker for compliance engine."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


class CheckSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CheckResult(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    ERROR = "error"  # could not run the check


@dataclass
class ComplianceCheck:
    """Result of a single compliance check."""
    check_id: str                        # e.g. "aws.bedrock.logging_enabled"
    check_name: str                      # human-readable
    category: str                        # encryption, access, logging, network, governance
    provider: str                        # aws, azure, gcp
    result: CheckResult
    severity: CheckSeverity
    details: dict = field(default_factory=dict)
    remediation: Optional[str] = None
    resource: Optional[str] = None       # ARN / resource id if applicable
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseChecker:
    """Abstract base for provider-specific compliance checkers."""

    provider: str = ""

    async def run_all(self) -> list[ComplianceCheck]:
        """Run all checks and return results. Subclasses override."""
        raise NotImplementedError
