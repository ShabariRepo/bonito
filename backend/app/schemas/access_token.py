import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class AccessTokenCreate(BaseModel):
    """Create a personal access token."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255)
    scopes: Optional[list[str]] = Field(None, description="Permission scopes. NULL = full access.")
    expires_in_days: int = Field(90, ge=1, le=365)
    rate_limit: int = Field(120, ge=1, le=10000)


class ProjectTokenCreate(BaseModel):
    """Create a project-scoped token."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255)
    expires_in_days: int = Field(90, ge=1, le=365)
    rate_limit: int = Field(120, ge=1, le=10000)


class AccessTokenResponse(BaseModel):
    """Token metadata (never includes the raw token)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    token_type: str
    name: str
    token_prefix: str
    scopes: Optional[list[str]] = None
    rate_limit: int
    expires_at: datetime
    last_used_at: Optional[datetime] = None
    created_at: datetime
    revoked_at: Optional[datetime] = None
    created_by_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None


class AccessTokenCreated(AccessTokenResponse):
    """Returned once on creation — includes the raw token."""

    token: str = Field(..., description="Raw token. Shown only once.")
