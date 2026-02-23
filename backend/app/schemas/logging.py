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
    metadata: Optional[Dict[str, Any]] = Field(None, validation_alias="event_metadata")
    duration_ms: Optional[int] = None
    cost: Optional[float] = None
    message: Optional[str] = None
    created_at: datetime

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
    enabled: Optional[bool] = None


class LogIntegrationResponse(BaseModel):
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
    export_format: str
    filters: Dict[str, Any]
    status: str
    progress: int
    total_records: Optional[int] = None
    processed_records: int
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

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
