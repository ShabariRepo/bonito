import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class OnboardingProgressResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    current_step: int
    completed: bool
    completion_percentage: int
    selected_providers: Optional[list[str]] = None
    selected_iac_tool: Optional[str] = None
    provider_credentials_validated: Optional[dict[str, bool]] = None
    step_timestamps: Optional[dict[str, str]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OnboardingProgressUpdate(BaseModel):
    current_step: Optional[int] = Field(None, ge=1, le=5)
    selected_providers: Optional[list[str]] = None
    selected_iac_tool: Optional[str] = None
    provider_credentials_validated: Optional[dict[str, bool]] = None
    completed: Optional[bool] = None


class IaCFile(BaseModel):
    filename: str
    content: str


class GenerateIaCRequest(BaseModel):
    provider: str = Field(..., pattern="^(aws|azure|gcp)$")
    iac_tool: str = Field(..., pattern="^(terraform|pulumi|cloudformation|bicep|manual)$")
    # Optional customization
    project_name: Optional[str] = "bonito"
    region: Optional[str] = None
    # AWS-specific
    aws_account_id: Optional[str] = None
    # Azure-specific
    azure_subscription_id: Optional[str] = None
    # GCP-specific
    gcp_project_id: Optional[str] = None


class GenerateIaCResponse(BaseModel):
    provider: str
    iac_tool: str
    code: str
    filename: str
    files: list[IaCFile] = []
    instructions: list[str]
    security_notes: list[str]


class ValidateCredentialsRequest(BaseModel):
    provider: str = Field(..., pattern="^(aws|azure|gcp)$")
    credentials: dict


class ConnectionHealth(BaseModel):
    """Health status for a validated provider connection."""
    provider: str
    status: str  # "healthy", "degraded", "error"
    latency_ms: Optional[int] = None
    checks: list[dict] = []  # [{name, status, message}]
    checked_at: datetime


class ValidateCredentialsResponse(BaseModel):
    provider: str
    valid: bool
    identity: Optional[str] = None
    permissions: Optional[list[str]] = None
    errors: Optional[list[str]] = None
    health: Optional[ConnectionHealth] = None
