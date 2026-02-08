from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.export_service import generate_terraform, generate_pulumi, get_supported_formats

router = APIRouter(prefix="/export", tags=["export"])


class ExportRequest(BaseModel):
    providers: Optional[List[str]] = None
    naming_prefix: str = "bonito"


class ExportResponse(BaseModel):
    format: str
    code: str
    filename: str


@router.get("/formats")
async def formats():
    return get_supported_formats()


@router.post("/terraform", response_model=ExportResponse)
async def terraform(req: ExportRequest):
    code = generate_terraform(req.providers, req.naming_prefix)
    return ExportResponse(format="terraform", code=code, filename=f"{req.naming_prefix}-infra.tf")


@router.post("/pulumi", response_model=ExportResponse)
async def pulumi(req: ExportRequest):
    code = generate_pulumi(req.providers, req.naming_prefix)
    return ExportResponse(format="pulumi", code=code, filename=f"{req.naming_prefix}-infra.ts")
