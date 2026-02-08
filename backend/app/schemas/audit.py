from datetime import datetime
from uuid import UUID
from typing import Optional, List

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: UUID
    org_id: UUID
    user_id: Optional[UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details_json: Optional[dict] = None
    ip_address: Optional[str] = None
    user_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
