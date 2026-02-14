from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DeploymentCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: UUID
    provider_id: Optional[UUID] = None  # Auto-detected from model if not provided
    config: dict = {}


class DeploymentUpdate(BaseModel):
    config: Optional[dict] = None
    status: Optional[str] = None


class DeploymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    org_id: UUID
    model_id: UUID
    provider_id: UUID
    config: dict
    status: str
    created_at: datetime
