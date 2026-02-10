from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.audit import AuditLogResponse, AuditLogListResponse
from app.services.audit_service import generate_mock_audit_logs

router = APIRouter(prefix="/audit", tags=["audit"])

_logs = generate_mock_audit_logs(50)


@router.get("/", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    user_name: Optional[str] = None,
    user: User = Depends(get_current_user),
):
    filtered = _logs
    if action:
        filtered = [l for l in filtered if l["action"] == action]
    if resource_type:
        filtered = [l for l in filtered if l["resource_type"] == resource_type]
    if user_name:
        filtered = [l for l in filtered if user_name.lower() in l["user_name"].lower()]

    total = len(filtered)
    start = (page - 1) * page_size
    items = filtered[start:start + page_size]

    return AuditLogListResponse(items=items, total=total, page=page, page_size=page_size)
