from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: str
    name: str
    role: str = "viewer"


class UserUpdate(BaseModel):
    role: str


class UserResponse(BaseModel):
    id: UUID
    org_id: UUID
    email: str
    name: str
    role: str
    avatar_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
