from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.compliance import (
    ComplianceCheckResponse,
    ComplianceStatus,
    FrameworkInfo,
    ComplianceReport,
    ScanResult,
)
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.compliance_service import (
    get_compliance_status,
    get_compliance_checks,
    get_frameworks,
    run_scan,
    get_compliance_report,
)

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/status", response_model=ComplianceStatus)
async def status(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await get_compliance_status(db, org_id=user.org_id)


@router.get("/checks", response_model=List[ComplianceCheckResponse])
async def checks(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await get_compliance_checks(db, org_id=user.org_id)


@router.post("/scan", response_model=ScanResult)
async def scan(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await run_scan(db, org_id=user.org_id)


@router.get("/frameworks", response_model=List[FrameworkInfo])
async def frameworks(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await get_frameworks(db, org_id=user.org_id)


@router.get("/report", response_model=ComplianceReport)
async def report(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return await get_compliance_report(db, org_id=user.org_id)
