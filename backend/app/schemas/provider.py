from datetime import datetime
from enum import Enum
from uuid import UUID
from typing import Optional, List

from pydantic import BaseModel, Field, model_validator


class ConnectionStatus(str, Enum):
    pending = "pending"
    active = "active"
    error = "error"
    disconnected = "disconnected"


class ProviderType(str, Enum):
    aws = "aws"
    azure = "azure"
    gcp = "gcp"


class AWSCredentials(BaseModel):
    access_key_id: str = Field(..., min_length=16)
    secret_access_key: str = Field(..., min_length=20)
    region: str = Field(default="us-east-1")


class AzureCredentials(BaseModel):
    tenant_id: str
    client_id: str
    client_secret: str
    subscription_id: str
    resource_group: str = ""
    endpoint: str = ""


class GCPCredentials(BaseModel):
    project_id: str
    service_account_json: str
    region: str = "us-central1"


_CREDENTIAL_SCHEMAS: dict[str, type[BaseModel]] = {
    "aws": AWSCredentials,
    "azure": AzureCredentials,
    "gcp": GCPCredentials,
}

# Fields allowed per provider (for strict rejection of unexpected keys)
_ALLOWED_FIELDS: dict[str, set[str]] = {
    "aws": {"access_key_id", "secret_access_key", "region"},
    "azure": {"tenant_id", "client_id", "client_secret", "subscription_id", "resource_group", "endpoint"},
    "gcp": {"project_id", "service_account_json", "region"},
}


class ProviderConnect(BaseModel):
    provider_type: ProviderType
    credentials: dict
    name: Optional[str] = None

    @model_validator(mode="after")
    def validate_credentials(self):
        pt = self.provider_type.value
        schema = _CREDENTIAL_SCHEMAS.get(pt)
        if not schema:
            raise ValueError(f"Unsupported provider type: {pt}")

        # Reject unexpected fields
        allowed = _ALLOWED_FIELDS[pt]
        unexpected = set(self.credentials.keys()) - allowed
        if unexpected:
            raise ValueError(f"Unexpected credential fields for {pt}: {', '.join(sorted(unexpected))}")

        # Sanitize string values — strip whitespace, reject empty
        sanitized = {}
        for k, v in self.credentials.items():
            if isinstance(v, str):
                v = v.strip()
                if not v:
                    raise ValueError(f"Credential field '{k}' cannot be empty")
            sanitized[k] = v
        self.credentials = sanitized

        # Validate against typed schema
        schema(**self.credentials)
        return self


class ProviderCreate(BaseModel):
    org_id: UUID
    provider_type: str
    credentials: Optional[dict] = None


class ProviderUpdate(BaseModel):
    provider_type: Optional[str] = None
    credentials: Optional[dict] = None
    status: Optional[str] = None


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    provider_model_id: str
    capabilities: List[str] = []
    context_window: int
    pricing_tier: str
    input_price_per_1k: Optional[float] = None
    output_price_per_1k: Optional[float] = None
    status: str = "available"


class ProviderResponse(BaseModel):
    id: UUID
    org_id: UUID
    provider_type: str
    status: str
    name: str = ""
    region: str = ""
    model_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class ProviderDetail(ProviderResponse):
    models: List[ModelInfo] = []
    last_verified: Optional[datetime] = None
    connection_health: str = "healthy"


class VerifyResponse(BaseModel):
    success: bool
    message: str
    latency_ms: Optional[float] = None
    account_id: Optional[str] = None
    model_count: Optional[int] = None
    region: Optional[str] = None


class InvocationRequest(BaseModel):
    model_id: str
    prompt: str
    max_tokens: int = Field(default=1024, ge=1, le=100000)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)


class InvocationResponse(BaseModel):
    response_text: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    estimated_cost: float = 0.0
    model_id: str = ""


class ProviderSummary(BaseModel):
    """Provider info with masked credentials — safe for API responses."""
    id: UUID
    provider_type: str
    status: str
    name: str = ""
    region: str = ""
    model_count: int = 0
    masked_credentials: dict = {}
    last_validated: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CredentialUpdate(BaseModel):
    """Update credentials for an existing provider."""
    credentials: dict


class DailyCostItem(BaseModel):
    date: str
    amount: float
    currency: str = "USD"
    service: str = ""
    usage_type: str = ""


class CostDataResponse(BaseModel):
    total: float
    currency: str = "USD"
    start_date: str = ""
    end_date: str = ""
    daily_costs: List[DailyCostItem] = []
