from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class DeploymentCreate(BaseModel):
    org_id: UUID
    model_id: UUID
    provider_id: UUID
    config: dict = {}


class DeploymentUpdate(BaseModel):
    config: Optional[dict] = None
    status: Optional[str] = None


class DeploymentResponse(BaseModel):
    id: UUID
    org_id: UUID
    model_id: UUID
    provider_id: UUID
    config: dict
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
