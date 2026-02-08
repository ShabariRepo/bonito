"""Abstract base class for cloud provider integrations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional


@dataclass
class ModelInfo:
    model_id: str
    model_name: str
    provider_name: str  # e.g. "Anthropic", "Meta", "Amazon"
    input_modalities: List[str] = field(default_factory=lambda: ["TEXT"])
    output_modalities: List[str] = field(default_factory=lambda: ["TEXT"])
    streaming_supported: bool = False
    context_window: int = 0
    input_price_per_1m_tokens: float = 0.0
    output_price_per_1m_tokens: float = 0.0
    status: str = "ACTIVE"
    capabilities: List[str] = field(default_factory=list)


@dataclass
class InvocationResult:
    response_text: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    estimated_cost: float = 0.0
    model_id: str = ""


@dataclass
class DailyCost:
    date: str
    amount: float
    currency: str = "USD"
    service: str = ""
    usage_type: str = ""


@dataclass
class CostData:
    total: float
    currency: str = "USD"
    start_date: str = ""
    end_date: str = ""
    daily_costs: List[DailyCost] = field(default_factory=list)


@dataclass
class HealthStatus:
    healthy: bool
    latency_ms: float = 0.0
    account_id: str = ""
    arn: str = ""
    message: str = ""


@dataclass
class CredentialInfo:
    valid: bool
    account_id: str = ""
    arn: str = ""
    user_id: str = ""
    message: str = ""


class CloudProvider(ABC):
    """Abstract base class for cloud provider integrations."""

    @abstractmethod
    async def validate_credentials(self) -> CredentialInfo:
        """Test if credentials are valid and return account info."""
        ...

    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """Get available models from the provider."""
        ...

    @abstractmethod
    async def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Get details for a single model."""
        ...

    @abstractmethod
    async def invoke_model(
        self, model_id: str, prompt: str, max_tokens: int = 1024, temperature: float = 0.7
    ) -> InvocationResult:
        """Invoke a model with a prompt."""
        ...

    @abstractmethod
    async def get_costs(self, start_date: date, end_date: date) -> CostData:
        """Get billing data for a date range."""
        ...

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Quick health check on the connection."""
        ...
