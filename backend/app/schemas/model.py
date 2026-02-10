from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class ModelCreate(BaseModel):
    provider_id: UUID
    model_id: str
    display_name: str
    capabilities: dict = {}
    pricing_info: dict = {}


class ModelUpdate(BaseModel):
    display_name: Optional[str] = None
    capabilities: Optional[dict] = None
    pricing_info: Optional[dict] = None


class ModelResponse(BaseModel):
    id: UUID
    provider_id: UUID
    provider_type: Optional[str] = None
    model_id: str
    display_name: str
    capabilities: dict
    pricing_info: dict
    created_at: datetime

    model_config = {"from_attributes": True}
