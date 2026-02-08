from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class OrgCreate(BaseModel):
    name: str


class OrgUpdate(BaseModel):
    name: Optional[str] = None


class OrgResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
