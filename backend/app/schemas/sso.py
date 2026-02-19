"""Pydantic schemas for SSO/SAML configuration."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SSOConfigBase(BaseModel):
    """Fields shared between create/update requests."""
    provider_type: str = Field(default="custom", pattern="^(okta|azure_ad|google|custom)$")
    idp_metadata_url: Optional[str] = None
    idp_sso_url: Optional[str] = None
    idp_entity_id: Optional[str] = None
    idp_certificate: Optional[str] = None
    attribute_mapping: Optional[dict] = None
    role_mapping: Optional[dict] = None


class SSOConfigUpdate(SSOConfigBase):
    """Request body for creating/updating SSO config."""
    breakglass_user_id: Optional[uuid.UUID] = None


class SSOConfigResponse(SSOConfigBase):
    """Response body for SSO config."""
    id: uuid.UUID
    org_id: uuid.UUID
    sp_entity_id: Optional[str] = None
    sp_acs_url: Optional[str] = None
    enabled: bool = False
    enforced: bool = False
    breakglass_user_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SSOEnforceRequest(BaseModel):
    """Request body for enforcing SSO."""
    breakglass_user_id: uuid.UUID


class SSOStatusResponse(BaseModel):
    """Lightweight SSO status for login page."""
    sso_enabled: bool = False
    sso_enforced: bool = False
    sso_login_url: Optional[str] = None
    provider_type: Optional[str] = None


class SSOLoginCheckRequest(BaseModel):
    """Request to check SSO status by email domain."""
    email: str
