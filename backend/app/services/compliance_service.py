"""Compliance service — runs real checks against connected providers."""

import json
import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_client
from app.core.vault import vault_client
from app.models.cloud_provider import CloudProvider
from app.schemas.compliance import (
    ComplianceCheckResponse,
    ComplianceStatus,
    FrameworkInfo,
    ComplianceReport,
    ScanResult,
)
from app.services.compliance.base import CheckResult, ComplianceCheck
from app.services.compliance.aws_checks import AWSComplianceChecker
from app.services.compliance.azure_checks import AzureComplianceChecker
from app.services.compliance.gcp_checks import GCPComplianceChecker
from app.services.compliance.frameworks import (
    FRAMEWORK_INFO,
    FRAMEWORK_MAPPING,
    get_frameworks_for_check,
)

logger = logging.getLogger(__name__)

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
CACHE_KEY = "compliance:results"
CACHE_TTL = 3600  # 1 hour


# ── Internal helpers ─────────────────────────────────────────────

async def _get_checker_for_provider(provider: CloudProvider):
    """Create a compliance checker from a DB provider record + Vault credentials."""
    vault_path = f"providers/{provider.id}"
    secrets = await vault_client.get_secrets(vault_path)
    if not secrets:
        return None

    if provider.provider_type == "aws":
        return AWSComplianceChecker(
            access_key_id=secrets["access_key_id"],
            secret_access_key=secrets["secret_access_key"],
            region=secrets.get("region", "us-east-1"),
        )
    elif provider.provider_type == "azure":
        return AzureComplianceChecker(
            tenant_id=secrets["tenant_id"],
            client_id=secrets["client_id"],
            client_secret=secrets["client_secret"],
            subscription_id=secrets["subscription_id"],
        )
    elif provider.provider_type == "gcp":
        return GCPComplianceChecker(
            project_id=secrets["project_id"],
            service_account_json=secrets["service_account_json"],
            region=secrets.get("region", "us-central1"),
        )
    return None


def _check_to_response(check: ComplianceCheck) -> ComplianceCheckResponse:
    """Convert internal ComplianceCheck to API response schema."""
    frameworks = get_frameworks_for_check(check.check_id)
    details = dict(check.details)
    if check.remediation:
        details["remediation"] = check.remediation
    if check.resource:
        details["resource"] = check.resource

    return ComplianceCheckResponse(
        id=uuid.uuid5(uuid.NAMESPACE_DNS, check.check_id),
        org_id=DEFAULT_ORG_ID,
        check_name=check.check_name,
        category=check.category,
        status=check.result.value,
        frameworks=frameworks,
        details=details,
        last_scanned=check.checked_at,
        created_at=check.checked_at,
    )


def _build_frameworks(checks: list[ComplianceCheckResponse]) -> list[FrameworkInfo]:
    """Aggregate per-framework stats from check results."""
    frameworks = []
    for fw_name, fw_meta in FRAMEWORK_INFO.items():
        fw_checks = [c for c in checks if fw_name in c.frameworks]
        fw_passing = sum(1 for c in fw_checks if c.status == "pass")
        frameworks.append(FrameworkInfo(
            name=fw_name,
            display_name=fw_meta["display_name"],
            description=fw_meta["description"],
            total_checks=len(fw_checks),
            passing_checks=fw_passing,
            coverage_pct=round((fw_passing / len(fw_checks)) * 100, 1) if fw_checks else 0,
        ))
    return frameworks


def _serialize_checks(checks: list[ComplianceCheckResponse]) -> str:
    return json.dumps([
        {
            "id": str(c.id),
            "org_id": str(c.org_id),
            "check_name": c.check_name,
            "category": c.category,
            "status": c.status,
            "frameworks": c.frameworks,
            "details": c.details,
            "last_scanned": c.last_scanned.isoformat(),
            "created_at": c.created_at.isoformat(),
        }
        for c in checks
    ])


def _deserialize_checks(data: str) -> list[ComplianceCheckResponse]:
    items = json.loads(data)
    return [
        ComplianceCheckResponse(
            id=uuid.UUID(i["id"]),
            org_id=uuid.UUID(i["org_id"]),
            check_name=i["check_name"],
            category=i["category"],
            status=i["status"],
            frameworks=i["frameworks"],
            details=i["details"],
            last_scanned=datetime.fromisoformat(i["last_scanned"]),
            created_at=datetime.fromisoformat(i["created_at"]),
        )
        for i in items
    ]


# ── Core engine ──────────────────────────────────────────────────

async def _run_checks(db: Optional[AsyncSession] = None) -> list[ComplianceCheckResponse]:
    """Run real compliance checks against all connected providers."""
    # Try cache first
    try:
        cached = await redis_client.get(CACHE_KEY)
        if cached:
            return _deserialize_checks(cached)
    except Exception:
        pass

    raw_checks: list[ComplianceCheck] = []

    if db:
        # Get all active providers from DB
        result = await db.execute(
            select(CloudProvider).where(CloudProvider.status == "active")
        )
        providers = result.scalars().all()

        for provider in providers:
            try:
                checker = await _get_checker_for_provider(provider)
                if checker:
                    provider_checks = await checker.run_all()
                    raw_checks.extend(provider_checks)
            except Exception as e:
                logger.error(f"Compliance checks failed for provider {provider.id}: {e}")

    # If no providers or no DB, return empty
    if not raw_checks:
        logger.info("No connected providers found; returning empty compliance results")
        return []

    # Convert to response format
    responses = [_check_to_response(c) for c in raw_checks]

    # Cache results
    try:
        await redis_client.setex(CACHE_KEY, CACHE_TTL, _serialize_checks(responses))
    except Exception:
        pass

    return responses


# ── Public API (used by routes) ──────────────────────────────────

async def get_compliance_status(db: Optional[AsyncSession] = None) -> ComplianceStatus:
    checks = await _run_checks(db)
    passing = sum(1 for c in checks if c.status == "pass")
    failing = sum(1 for c in checks if c.status == "fail")
    warnings = sum(1 for c in checks if c.status in ("warning", "error"))
    total = len(checks)
    score = round((passing / total) * 100, 1) if total > 0 else 0

    return ComplianceStatus(
        overall_score=score,
        total_checks=total,
        passing=passing,
        failing=failing,
        warnings=warnings,
        frameworks=_build_frameworks(checks),
        last_scan=checks[0].last_scanned if checks else None,
    )


async def get_compliance_checks(db: Optional[AsyncSession] = None) -> list[ComplianceCheckResponse]:
    return await _run_checks(db)


async def get_frameworks(db: Optional[AsyncSession] = None) -> list[FrameworkInfo]:
    return (await get_compliance_status(db)).frameworks


async def run_scan(db: Optional[AsyncSession] = None) -> ScanResult:
    # Invalidate cache to force fresh scan
    try:
        await redis_client.delete(CACHE_KEY)
    except Exception:
        pass

    start = time.monotonic()
    checks = await _run_checks(db)
    duration_ms = int((time.monotonic() - start) * 1000)

    return ScanResult(
        scan_id=str(uuid.uuid4())[:8],
        checks_run=len(checks),
        passed=sum(1 for c in checks if c.status == "pass"),
        failed=sum(1 for c in checks if c.status == "fail"),
        warnings=sum(1 for c in checks if c.status in ("warning", "error")),
        duration_ms=duration_ms,
    )


async def get_compliance_report(db: Optional[AsyncSession] = None) -> ComplianceReport:
    status = await get_compliance_status(db)
    checks = await _run_checks(db)
    recommendations = []
    for c in checks:
        if c.status == "fail":
            rem = c.details.get("remediation", f"Fix {c.check_name}")
            recommendations.append(f"CRITICAL: {rem}")
        elif c.status in ("warning", "error"):
            rem = c.details.get("remediation", f"Review {c.check_name}")
            recommendations.append(f"WARNING: {rem}")
    return ComplianceReport(
        generated_at=datetime.now(timezone.utc),
        overall_score=status.overall_score,
        frameworks=status.frameworks,
        checks=checks,
        recommendations=recommendations,
    )
