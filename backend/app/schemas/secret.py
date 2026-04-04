from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class SecretCreate(BaseModel):
    """Request to create a new org secret."""
    name: str
    value: str
    description: Optional[str] = None


class SecretUpdate(BaseModel):
    """Request to update an existing secret."""
    value: str
    description: Optional[str] = None


class SecretListItem(BaseModel):
    """Secret metadata (no value) for list endpoint."""
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SecretDetail(BaseModel):
    """Full secret details including value."""
    name: str
    value: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
