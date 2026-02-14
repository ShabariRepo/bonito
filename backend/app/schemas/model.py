from datetime import datetime
from uuid import UUID
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict


class ModelCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

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
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    provider_id: UUID
    provider_type: Optional[str] = None
    model_id: str
    display_name: str
    capabilities: dict
    pricing_info: dict
    status: Optional[str] = None
    created_at: datetime


class UsageStats(BaseModel):
    total_requests: int
    total_tokens: int
    total_cost: float
    requests_by_day: List[Dict[str, Any]]


class ProviderInfo(BaseModel):
    id: UUID
    provider_type: str
    status: str
    region: Optional[str] = None


class ModelDetailsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID
    provider_id: UUID
    model_id: str
    display_name: str
    provider_type: str
    capabilities: dict
    pricing_info: dict
    created_at: datetime
    provider_info: ProviderInfo
    usage_stats: UsageStats
    context_window: Optional[int] = None
    input_price_per_1k: Optional[float] = None
    output_price_per_1k: Optional[float] = None


class PlaygroundMessage(BaseModel):
    role: str
    content: str


class PlaygroundRequest(BaseModel):
    messages: List[PlaygroundMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000


class PlaygroundUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class PlaygroundResponse(BaseModel):
    response: str
    usage: PlaygroundUsage
    cost: float
    latency_ms: int
    provider: str


class CompareRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_ids: List[UUID]
    messages: List[PlaygroundMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000


class CompareResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_id: UUID
    display_name: str
    response: str
    usage: PlaygroundUsage
    cost: float
    latency_ms: int
    provider: str
    error: Optional[str] = None


class CompareResponse(BaseModel):
    results: List[CompareResult]
