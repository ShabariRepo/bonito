from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# ─── Project Schemas ───

class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    budget_monthly: Optional[Decimal] = Field(default=None)
    settings: Optional[Dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern=r"^(active|paused|archived)$")
    budget_monthly: Optional[Decimal] = Field(default=None)
    settings: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    description: Optional[str]
    status: str
    budget_monthly: Optional[Decimal]
    budget_spent: Decimal
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    # Derived fields
    agent_count: Optional[int] = None

    class Config:
        from_attributes = True


# ─── Agent Schemas ───

class AgentCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    system_prompt: str = Field(..., min_length=1)
    model_id: str = Field("auto", max_length=100)
    model_config: Optional[Dict[str, Any]] = None
    knowledge_base_ids: Optional[List[UUID]] = None
    tool_policy: Optional[Dict[str, Any]] = None
    max_turns: Optional[int] = Field(25, ge=1, le=100)
    timeout_seconds: Optional[int] = Field(300, ge=30, le=3600)
    compaction_enabled: Optional[bool] = True
    max_session_messages: Optional[int] = Field(200, ge=10, le=1000)
    rate_limit_rpm: Optional[int] = Field(30, ge=1, le=1000)
    budget_alert_threshold: Optional[Decimal] = Field(Decimal("0.8"), ge=Decimal("0.1"), le=Decimal("1.0"))


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(None, min_length=1)
    model_id: Optional[str] = Field(None, max_length=100)
    model_config: Optional[Dict[str, Any]] = None
    knowledge_base_ids: Optional[List[UUID]] = None
    tool_policy: Optional[Dict[str, Any]] = None
    max_turns: Optional[int] = Field(None, ge=1, le=100)
    timeout_seconds: Optional[int] = Field(None, ge=30, le=3600)
    compaction_enabled: Optional[bool] = None
    max_session_messages: Optional[int] = Field(None, ge=10, le=1000)
    rate_limit_rpm: Optional[int] = Field(None, ge=1, le=1000)
    budget_alert_threshold: Optional[Decimal] = Field(None, ge=Decimal("0.1"), le=Decimal("1.0"))
    status: Optional[str] = Field(None, pattern=r"^(active|paused|disabled)$")


class AgentResponse(BaseModel):
    id: UUID
    project_id: UUID
    org_id: UUID
    name: str
    description: Optional[str]
    system_prompt: str
    model_id: str
    model_config: Dict[str, Any]
    knowledge_base_ids: List[UUID]
    tool_policy: Dict[str, Any]
    max_turns: int
    timeout_seconds: int
    compaction_enabled: bool
    max_session_messages: int
    rate_limit_rpm: int
    budget_alert_threshold: Decimal
    status: str
    last_active_at: Optional[datetime]
    total_runs: int
    total_tokens: int
    total_cost: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentDetailResponse(AgentResponse):
    """Agent details with recent sessions and additional metrics."""
    recent_sessions: Optional[List["AgentSessionResponse"]] = None
    knowledge_bases: Optional[List[Dict[str, Any]]] = None  # KB details if requested


# ─── Session Schemas ───

class AgentSessionResponse(BaseModel):
    id: UUID
    agent_id: UUID
    org_id: UUID
    session_key: str
    title: Optional[str] = None
    status: str
    message_count: int
    total_tokens: int
    total_cost: Decimal
    session_metadata: Optional[Dict[str, Any]] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Message Schemas ───

class AgentMessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    org_id: UUID
    role: str
    content: Optional[str]
    tool_calls: Optional[Dict[str, Any]]
    tool_call_id: Optional[str]
    tool_name: Optional[str]
    is_compaction_summary: bool
    model_used: Optional[str]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    cost: Optional[Decimal]
    latency_ms: Optional[int]
    sequence: int
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Connection Schemas ───

class AgentConnectionCreate(BaseModel):
    target_agent_id: UUID
    connection_type: str = Field(..., pattern=r"^(handoff|escalation|data_feed|trigger)$")
    label: Optional[str] = Field(None, max_length=255)
    condition: Optional[Dict[str, Any]] = None
    enabled: bool = True


class AgentConnectionResponse(BaseModel):
    id: UUID
    project_id: UUID
    org_id: UUID
    source_agent_id: UUID
    target_agent_id: UUID
    connection_type: str
    label: Optional[str]
    condition: Optional[Dict[str, Any]]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    
    # Populated from joins
    source_agent_name: Optional[str] = None
    target_agent_name: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Trigger Schemas ───

class AgentTriggerCreate(BaseModel):
    trigger_type: str = Field(..., pattern=r"^(webhook|schedule|event|manual|api)$")
    config: Optional[Dict[str, Any]] = None
    enabled: bool = True


class AgentTriggerResponse(BaseModel):
    id: UUID
    agent_id: UUID
    org_id: UUID
    trigger_type: str
    config: Dict[str, Any]
    enabled: bool
    last_fired_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Execution Schemas ───

class AgentExecuteRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    session_id: Optional[UUID] = None  # if not provided, creates new session


class SecurityMetadata(BaseModel):
    """Security metadata for agent execution."""
    tools_used: List[str]
    knowledge_bases_accessed: List[str]
    budget_remaining: Optional[Decimal]
    budget_percent_used: Optional[Decimal]
    input_sanitized: bool
    audit_id: UUID
    rate_limit_remaining: int


class AgentRunResult(BaseModel):
    """Result from running an agent."""
    content: Optional[str]
    tokens: int
    cost: Decimal
    turns: int
    model_used: Optional[str]
    security: SecurityMetadata


class AgentExecuteResponse(BaseModel):
    run_id: UUID
    session_id: UUID
    agent_id: UUID
    content: Optional[str]
    tokens: int
    cost: Decimal
    turns: int
    model_used: Optional[str]
    security: SecurityMetadata
    created_at: datetime


# ─── Agent Group Schemas ───

class AgentGroupCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    knowledge_base_ids: Optional[List[UUID]] = None
    budget_limit: Optional[Decimal] = None
    model_allowlist: Optional[List[str]] = None
    tool_policy: Optional[Dict[str, Any]] = None
    canvas_position: Optional[Dict[str, float]] = None
    canvas_style: Optional[Dict[str, str]] = None


class AgentGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    knowledge_base_ids: Optional[List[UUID]] = None
    budget_limit: Optional[Decimal] = None
    model_allowlist: Optional[List[str]] = None
    tool_policy: Optional[Dict[str, Any]] = None
    canvas_position: Optional[Dict[str, float]] = None
    canvas_style: Optional[Dict[str, str]] = None


class AgentGroupResponse(BaseModel):
    id: UUID
    project_id: UUID
    org_id: UUID
    name: str
    description: Optional[str]
    knowledge_base_ids: List[UUID]
    budget_limit: Optional[Decimal]
    model_allowlist: List[str]
    tool_policy: Dict[str, Any]
    canvas_position: Dict[str, float]
    canvas_style: Dict[str, str]
    created_at: datetime
    updated_at: datetime
    
    # Derived fields
    agent_count: Optional[int] = None
    knowledge_bases: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True


# ─── Role Schemas ───

class RoleCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    permissions: List[Dict[str, Any]] = Field(..., min_items=1)


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    permissions: Optional[List[Dict[str, Any]]] = None


class RoleResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    description: Optional[str]
    is_managed: bool
    permissions: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Role Assignment Schemas ───

from enum import Enum

class ScopeType(str, Enum):
    ORG = "org"
    PROJECT = "project"
    GROUP = "group"


class RoleAssignmentCreate(BaseModel):
    user_id: UUID
    role_id: UUID
    scope_type: ScopeType
    scope_id: Optional[UUID] = None


class RoleAssignmentResponse(BaseModel):
    id: UUID
    user_id: UUID
    role_id: UUID
    org_id: UUID
    scope_type: ScopeType
    scope_id: Optional[UUID]
    created_at: datetime
    
    # Populated from joins
    user_name: Optional[str] = None
    role_name: Optional[str] = None
    scope_name: Optional[str] = None  # Project or group name

    class Config:
        from_attributes = True


class UserPermissionResponse(BaseModel):
    """Response for user's effective permissions."""
    user_id: UUID
    permissions: List[Dict[str, Any]]
    role_assignments: List[RoleAssignmentResponse]


# ─── Graph Schemas ───

class GraphNode(BaseModel):
    id: UUID
    type: str  # "agent", "trigger", or "group"
    data: Dict[str, Any]  # node-specific data
    position: Optional[Dict[str, float]] = None  # {x: float, y: float}
    parentNode: Optional[UUID] = None  # for agents in groups
    extent: Optional[str] = None  # "parent" for constrained nodes


class GraphEdge(BaseModel):
    id: UUID
    source: UUID
    target: UUID
    type: str
    data: Dict[str, Any]  # edge-specific data (label, etc.)


class ProjectGraphResponse(BaseModel):
    project_id: UUID
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# Forward reference resolution
AgentDetailResponse.model_rebuild()