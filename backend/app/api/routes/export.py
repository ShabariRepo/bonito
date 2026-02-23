from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.feature_gate import feature_gate

from app.services.export_service import generate_terraform, generate_pulumi, get_supported_formats

router = APIRouter(prefix="/export", tags=["export"])


async def _require_iac_templates(db: AsyncSession, user: User):
    """Check that the organization has access to the iac_templates feature."""
    await feature_gate.require_feature(db, str(user.org_id), "iac_templates")


class ExportRequest(BaseModel):
    providers: Optional[List[str]] = None
    naming_prefix: str = "bonito"


class ExportResponse(BaseModel):
    format: str
    code: str
    filename: str


@router.get("/formats")
async def formats(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await _require_iac_templates(db, user)
    return get_supported_formats()


@router.post("/terraform", response_model=ExportResponse)
async def terraform(req: ExportRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await _require_iac_templates(db, user)
    code = generate_terraform(req.providers, req.naming_prefix)
    return ExportResponse(format="terraform", code=code, filename=f"{req.naming_prefix}-infra.tf")


@router.post("/pulumi", response_model=ExportResponse)
async def pulumi(req: ExportRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await _require_iac_templates(db, user)
    code = generate_pulumi(req.providers, req.naming_prefix)
    return ExportResponse(format="pulumi", code=code, filename=f"{req.naming_prefix}-infra.ts")
