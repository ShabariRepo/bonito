<<<<<<< HEAD
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ─── Log Enums and Constants ───

LOG_TYPES = [
    "gateway",
    "agent", 
    "auth",
    "admin",
    "kb",
    "deployment",
    "billing"
]

SEVERITIES = [
    "debug",
    "info", 
    "warn",
    "error",
    "critical"
]

RESOURCE_TYPES = [
    "model",
    "agent",
    "project", 
    "group",
    "kb",
    "deployment",
    "policy",
    "user",
    "organization"
]

ACTIONS = [
    "create",
    "read", 
    "update",
    "delete",
    "execute",
    "search",
    "authenticate",
    "authorize"
]

INTEGRATION_TYPES = [
    "datadog",
    "splunk", 
    "cloudwatch",
    "elasticsearch",
    "opensearch",
    "azure_monitor",
    "google_cloud_logging",
    "webhook",
    "s3",
    "gcs",
    "azure_blob"
]

EXPORT_FORMATS = [
    "csv",
    "json",
    "parquet"
]

EXPORT_STATUSES = [
    "pending",
    "running",
    "completed",
    "failed"
]


# ─── Core Schemas ───

class LogEntry(BaseModel):
    """Schema for emitting new log entries."""
    
    org_id: UUID
    log_type: str = Field(..., pattern=f"^({'|'.join(LOG_TYPES)})$")
    event_type: str = Field(..., min_length=1, max_length=100)
    severity: str = Field(..., pattern=f"^({'|'.join(SEVERITIES)})$")
    trace_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    resource_id: Optional[UUID] = None
    resource_type: Optional[str] = Field(None, pattern=f"^({'|'.join(RESOURCE_TYPES)})$")
    action: Optional[str] = Field(None, pattern=f"^({'|'.join(ACTIONS)})$")
    metadata: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = Field(None, ge=0)
    cost: Optional[float] = Field(None, ge=0.0)
    message: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "org_id": "550e8400-e29b-41d4-a716-446655440000",
                "log_type": "gateway",
                "event_type": "request",
                "severity": "info",
                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                "resource_type": "model", 
                "action": "execute",
                "metadata": {
                    "model": "gpt-4o",
                    "provider": "openai",
                    "tokens": 1500
                },
                "duration_ms": 2500,
                "cost": 0.045,
                "message": "Completed chat completion request"
            }
        }
    )


class PlatformLogResponse(BaseModel):
    """Response schema for platform log entries."""
    
=======
"""Pydantic schemas for the logging and observability system."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field


# ── Enums ──

class LogType(str, Enum):
    gateway = "gateway"
    auth = "auth"
    agent = "agent"
    kb = "kb"
    admin = "admin"
    deployment = "deployment"
    billing = "billing"
    compliance = "compliance"


class Severity(str, Enum):
    debug = "debug"
    info = "info"
    warn = "warn"
    error = "error"
    critical = "critical"


class IntegrationType(str, Enum):
    datadog = "datadog"
    splunk = "splunk"
    cloudwatch = "cloudwatch"
    elasticsearch = "elasticsearch"
    azure_monitor = "azure_monitor"
    gcp_logging = "gcp_logging"
    webhook = "webhook"
    cloud_storage = "cloud_storage"


class ExportFormat(str, Enum):
    csv = "csv"
    json = "json"


class ExportStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


# ── Platform Log Schemas ──

class PlatformLogResponse(BaseModel):
>>>>>>> main
    id: UUID
    org_id: UUID
    log_type: str
    event_type: str
    severity: str
    trace_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    resource_id: Optional[UUID] = None
    resource_type: Optional[str] = None
    action: Optional[str] = None
<<<<<<< HEAD
    metadata: Optional[Dict[str, Any]] = None
=======
    metadata: Optional[Dict[str, Any]] = Field(None, validation_alias="event_metadata")
>>>>>>> main
    duration_ms: Optional[int] = None
    cost: Optional[float] = None
    message: Optional[str] = None
    created_at: datetime

<<<<<<< HEAD
    model_config = ConfigDict(from_attributes=True)


# ─── Integration Schemas ───

class LogIntegrationCreate(BaseModel):
    """Schema for creating log integrations."""
    
    name: str = Field(..., min_length=1, max_length=255)
    integration_type: str = Field(..., pattern=f"^({'|'.join(INTEGRATION_TYPES)})$")
    config: Dict[str, Any] = Field(..., description="Integration-specific configuration")
    credentials: Dict[str, str] = Field(..., description="Credentials (will be stored in Vault)")
    enabled: bool = True

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Production Datadog",
                "integration_type": "datadog",
                "config": {
                    "site": "datadoghq.com",
                    "service": "bonito-platform",
                    "source": "bonito",
                    "tags": ["env:prod", "service:bonito"]
                },
                "credentials": {
                    "api_key": "your-datadog-api-key"
                },
                "enabled": True
            }
        }
    )


class LogIntegrationUpdate(BaseModel):
    """Schema for updating log integrations."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[Dict[str, Any]] = None
    credentials: Optional[Dict[str, str]] = None
=======
    model_config = {"from_attributes": True, "populate_by_name": True}


class PlatformLogListResponse(BaseModel):
    items: List[PlatformLogResponse]
    total: int
    page: int
    page_size: int


# ── Log Integration Schemas ──

class LogIntegrationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    integration_type: IntegrationType
    config: Dict[str, Any] = Field(default_factory=dict, description="Non-sensitive integration config (e.g. region, index name)")
    credentials: Dict[str, Any] = Field(..., description="Sensitive credentials (API keys, tokens). Stored encrypted, never returned.")
    enabled: bool = True


class LogIntegrationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[Dict[str, Any]] = None
    credentials: Optional[Dict[str, Any]] = Field(None, description="If provided, replaces existing credentials")
>>>>>>> main
    enabled: Optional[bool] = None


class LogIntegrationResponse(BaseModel):
<<<<<<< HEAD
    """Response schema for log integrations."""
    
=======
>>>>>>> main
    id: UUID
    org_id: UUID
    name: str
    integration_type: str
    config: Dict[str, Any]
    enabled: bool
    last_test_status: Optional[str] = None
    last_test_message: Optional[str] = None
    last_test_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

<<<<<<< HEAD
    model_config = ConfigDict(from_attributes=True)


class LogIntegrationTestResult(BaseModel):
    """Result of testing a log integration."""
    
    success: bool
    message: str
    response_time_ms: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


# ─── Query and Filter Schemas ───

class LogQueryFilters(BaseModel):
    """Filters for querying platform logs."""
    
    log_types: Optional[List[str]] = Field(None, description="Filter by log types")
    event_types: Optional[List[str]] = Field(None, description="Filter by event types")
    severities: Optional[List[str]] = Field(None, description="Filter by severities")
    user_ids: Optional[List[UUID]] = Field(None, description="Filter by user IDs")
    resource_types: Optional[List[str]] = Field(None, description="Filter by resource types")
    resource_ids: Optional[List[UUID]] = Field(None, description="Filter by resource IDs")
    actions: Optional[List[str]] = Field(None, description="Filter by actions")
    trace_id: Optional[UUID] = Field(None, description="Filter by trace ID")
    start_date: Optional[datetime] = Field(None, description="Start date (inclusive)")
    end_date: Optional[datetime] = Field(None, description="End date (exclusive)")
    search: Optional[str] = Field(None, description="Full-text search in message and metadata")
    min_duration_ms: Optional[int] = Field(None, ge=0, description="Minimum duration filter")
    max_duration_ms: Optional[int] = Field(None, ge=0, description="Maximum duration filter")
    min_cost: Optional[float] = Field(None, ge=0.0, description="Minimum cost filter")
    max_cost: Optional[float] = Field(None, ge=0.0, description="Maximum cost filter")


class LogQueryRequest(BaseModel):
    """Request schema for querying logs."""
    
    filters: LogQueryFilters = Field(default_factory=LogQueryFilters)
    limit: int = Field(100, ge=1, le=1000, description="Number of results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip")
    sort_by: str = Field("created_at", description="Field to sort by")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "filters": {
                    "log_types": ["gateway", "auth"],
                    "severities": ["error", "critical"],
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-01-31T23:59:59Z"
                },
                "limit": 50,
                "offset": 0,
                "sort_by": "created_at",
                "sort_order": "desc"
            }
        }
    )


class LogQueryResponse(BaseModel):
    """Response schema for log queries."""
    
    logs: List[PlatformLogResponse]
    total_count: int
    has_more: bool
    filters_applied: LogQueryFilters


# ─── Export Schemas ───

class LogExportRequest(BaseModel):
    """Request schema for exporting logs."""
    
    filters: LogQueryFilters = Field(default_factory=LogQueryFilters)
    export_format: str = Field(..., pattern=f"^({'|'.join(EXPORT_FORMATS)})$")
    include_metadata: bool = Field(True, description="Include metadata in export")
    email_when_complete: bool = Field(False, description="Send email notification when export completes")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "filters": {
                    "log_types": ["gateway"],
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-01-31T23:59:59Z"
                },
                "export_format": "csv",
                "include_metadata": True,
                "email_when_complete": True
            }
        }
    )


class LogExportJobResponse(BaseModel):
    """Response schema for export jobs."""
    
    id: UUID
    org_id: UUID
    user_id: UUID
=======
    model_config = {"from_attributes": True}


class LogIntegrationListResponse(BaseModel):
    items: List[LogIntegrationResponse]
    total: int


class LogIntegrationTestResult(BaseModel):
    success: bool
    message: str
    tested_at: datetime


# ── Log Export Schemas ──

class LogExportRequest(BaseModel):
    format: ExportFormat = ExportFormat.csv
    log_type: Optional[str] = None
    event_type: Optional[str] = None
    severity: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    resource_type: Optional[str] = None


class LogExportJobResponse(BaseModel):
    id: UUID
    org_id: UUID
>>>>>>> main
    export_format: str
    filters: Dict[str, Any]
    status: str
    progress: int
    total_records: Optional[int] = None
    processed_records: int
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
<<<<<<< HEAD
    download_expires_at: Optional[datetime] = None
=======
>>>>>>> main
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

<<<<<<< HEAD
    model_config = ConfigDict(from_attributes=True)


# ─── Analytics Schemas ───

class LogStatsRequest(BaseModel):
    """Request schema for log statistics."""
    
    filters: LogQueryFilters = Field(default_factory=LogQueryFilters)
    group_by: List[str] = Field(default=["log_type"], description="Fields to group by")
    metrics: List[str] = Field(
        default=["count", "error_rate"], 
        description="Metrics to calculate"
    )
    time_granularity: str = Field(
        "day", 
        pattern="^(hour|day|week|month)$",
        description="Time granularity for time-series data"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "filters": {
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-01-31T23:59:59Z"
                },
                "group_by": ["log_type", "severity"],
                "metrics": ["count", "error_rate", "avg_duration"],
                "time_granularity": "day"
            }
        }
    )


class LogStatsDataPoint(BaseModel):
    """Single data point in log statistics."""
    
    dimensions: Dict[str, str] = Field(..., description="Dimension values")
    metrics: Dict[str, float] = Field(..., description="Calculated metrics")
    timestamp: Optional[datetime] = Field(None, description="Timestamp for time-series data")


class LogStatsResponse(BaseModel):
    """Response schema for log statistics."""
    
    data: List[LogStatsDataPoint]
    total_records: int
    time_range: Optional[Dict[str, datetime]] = None
    filters_applied: LogQueryFilters


# ─── Aggregation Schemas ───

class LogAggregationResponse(BaseModel):
    """Response schema for log aggregations."""
    
    id: UUID
    org_id: UUID
    date_bucket: date
    hour_bucket: Optional[int] = None
    log_type: Optional[str] = None
    event_type: Optional[str] = None
    severity: Optional[str] = None
    log_count: int
    error_count: int
    total_duration_ms: Optional[int] = None
    total_cost: Optional[float] = None
    unique_users: Optional[int] = None
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)
=======
    model_config = {"from_attributes": True}


# ── Log Stats Schemas ──

class LogStatsBucket(BaseModel):
    date: str  # ISO date or datetime
    log_type: Optional[str] = None
    severity: Optional[str] = None
    count: int
    error_count: int = 0
    total_duration_ms: Optional[int] = None
    total_cost: Optional[float] = None


class LogStatsResponse(BaseModel):
    total_logs: int
    total_errors: int
    time_series: List[LogStatsBucket]
    by_type: Dict[str, int]
    by_severity: Dict[str, int]
    range_days: int
>>>>>>> main
