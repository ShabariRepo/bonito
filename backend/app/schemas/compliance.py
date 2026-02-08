from datetime import datetime
from uuid import UUID
from typing import Optional, List

from pydantic import BaseModel


class ComplianceCheckResponse(BaseModel):
    id: UUID
    org_id: UUID
    check_name: str
    category: str
    status: str
    frameworks: list
    details: dict
    last_scanned: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class FrameworkInfo(BaseModel):
    name: str
    display_name: str
    description: str
    total_checks: int
    passing_checks: int
    coverage_pct: float


class ComplianceStatus(BaseModel):
    overall_score: float
    total_checks: int
    passing: int
    failing: int
    warnings: int
    frameworks: List[FrameworkInfo]
    last_scan: Optional[datetime] = None


class ComplianceReport(BaseModel):
    generated_at: datetime
    overall_score: float
    frameworks: List[FrameworkInfo]
    checks: List[ComplianceCheckResponse]
    recommendations: List[str]


class ScanResult(BaseModel):
    scan_id: str
    checks_run: int
    passed: int
    failed: int
    warnings: int
    duration_ms: int
