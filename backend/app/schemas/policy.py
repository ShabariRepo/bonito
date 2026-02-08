from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class PolicyCreate(BaseModel):
    name: str
    type: str
    rules_json: dict = {}
    description: Optional[str] = None
    enabled: bool = True


class PolicyUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    rules_json: Optional[dict] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


class PolicyResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    type: str
    rules_json: dict
    description: Optional[str] = None
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}
