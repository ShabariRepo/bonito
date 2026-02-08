import uuid
from datetime import datetime
from typing import Optional, List, Any
from enum import Enum

from pydantic import BaseModel, Field


# ─── Routing Strategy ───

class RoutingStrategy(str, Enum):
    cost_optimized = "cost-optimized"
    latency_optimized = "latency-optimized"
    balanced = "balanced"
    failover = "failover"


# ─── OpenAI-compatible schemas ───

class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = None
    name: Optional[str] = None
    function_call: Optional[dict] = None
    tool_calls: Optional[List[dict]] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Any] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    user: Optional[str] = None


class CompletionRequest(BaseModel):
    model: str
    prompt: Any
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Any] = None


class EmbeddingRequest(BaseModel):
    model: str
    input: Any  # str or list of str
    encoding_format: Optional[str] = None


# ─── API Key schemas ───

class GatewayKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    team_id: Optional[str] = None
    rate_limit: int = Field(default=60, ge=1, le=10000)


class GatewayKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    team_id: Optional[str] = None
    rate_limit: int
    created_at: datetime
    revoked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GatewayKeyCreated(GatewayKeyResponse):
    """Returned only on creation — includes the full key (shown once)."""
    key: str


# ─── Usage / Logs ───

class GatewayLogEntry(BaseModel):
    id: uuid.UUID
    model_requested: str
    model_used: Optional[str] = None
    provider: Optional[str] = None
    input_tokens: int
    output_tokens: int
    cost: float
    latency_ms: int
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UsageSummary(BaseModel):
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost: float
    by_model: List[dict] = []
    by_day: List[dict] = []


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = ""
