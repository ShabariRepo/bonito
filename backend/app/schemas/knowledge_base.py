import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field


# ─── Enums ───

class SourceType(str, Enum):
    s3 = "s3"
    azure_blob = "azure_blob"
    gcs = "gcs"
    upload = "upload"


class KBStatus(str, Enum):
    pending = "pending"
    syncing = "syncing"
    ready = "ready"
    error = "error"


class DocumentStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    error = "error"


# ─── Knowledge Base schemas ───

class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    source_type: SourceType
    source_config: Dict[str, Any] = Field(default_factory=dict)
    embedding_model: str = Field(default="auto", max_length=100)
    embedding_dimensions: int = Field(default=1536, ge=1, le=4096)
    chunk_size: int = Field(default=512, ge=100, le=2048)
    chunk_overlap: int = Field(default=50, ge=0, le=200)
    sync_schedule: Optional[str] = None


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    source_config: Optional[Dict[str, Any]] = None
    embedding_model: Optional[str] = Field(None, max_length=100)
    embedding_dimensions: Optional[int] = Field(None, ge=1, le=4096)
    chunk_size: Optional[int] = Field(None, ge=100, le=2048)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=200)
    sync_schedule: Optional[str] = None


class KnowledgeBaseResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: Optional[str]
    source_type: SourceType
    source_config: Dict[str, Any]
    embedding_model: str
    embedding_dimensions: int
    chunk_size: int
    chunk_overlap: int
    status: KBStatus
    document_count: int
    chunk_count: int
    total_tokens: int
    last_synced_at: Optional[datetime]
    sync_schedule: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Document schemas ───

class KBDocumentCreate(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=500)
    file_path: Optional[str] = Field(None, max_length=1000)
    file_type: Optional[str] = Field(None, max_length=20)
    file_size: Optional[int] = Field(None, ge=0)
    file_hash: Optional[str] = Field(None, max_length=64)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KBDocumentResponse(BaseModel):
    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    org_id: uuid.UUID
    file_name: str
    file_path: Optional[str]
    file_type: Optional[str]
    file_size: Optional[int]
    file_hash: Optional[str]
    status: DocumentStatus
    chunk_count: int
    error_message: Optional[str]
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="extra_metadata")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


# ─── Chunk schemas ───

class KBChunkCreate(BaseModel):
    content: str = Field(..., min_length=1)
    token_count: Optional[int] = Field(None, ge=0)
    chunk_index: Optional[int] = Field(None, ge=0)
    embedding: Optional[List[float]] = None
    source_file: Optional[str] = Field(None, max_length=500)
    source_page: Optional[int] = Field(None, ge=1)
    source_section: Optional[str] = Field(None, max_length=500)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KBChunkResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    org_id: uuid.UUID
    content: str
    token_count: Optional[int]
    chunk_index: Optional[int]
    source_file: Optional[str]
    source_page: Optional[int]
    source_section: Optional[str]
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="extra_metadata")
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


# ─── Search schemas ───

class KBSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=50)
    min_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    filters: Optional[Dict[str, Any]] = None


class KBSearchResult(BaseModel):
    chunk_id: uuid.UUID
    content: str
    score: float
    source_file: Optional[str]
    source_page: Optional[int]
    source_section: Optional[str]
    document_id: uuid.UUID
    document_name: str
    metadata: Dict[str, Any]


class KBSearchResponse(BaseModel):
    query: str
    results: List[KBSearchResult]
    total_results: int
    search_time_ms: int


# ─── Sync schemas ───

class KBSyncRequest(BaseModel):
    force: bool = Field(default=False)


class KBSyncStatus(BaseModel):
    knowledge_base_id: uuid.UUID
    status: KBStatus
    progress_percentage: Optional[int] = None
    files_processed: int = 0
    files_total: int = 0
    current_file: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None


# ─── Upload schemas ───

class KBUploadResponse(BaseModel):
    document_id: uuid.UUID
    file_name: str
    file_size: int
    status: DocumentStatus
    message: str


# ─── Statistics schemas ───

class KBStats(BaseModel):
    total_documents: int
    total_chunks: int
    total_tokens: int
    document_types: Dict[str, int]  # {"pdf": 5, "docx": 3, ...}
    status_counts: Dict[str, int]  # {"ready": 8, "processing": 2, ...}
    avg_chunk_size: float
    last_sync: Optional[datetime]


# ─── Gateway integration schemas (for RAG) ───

class RAGContext(BaseModel):
    """Context injected into chat completion requests when using knowledge base."""
    knowledge_base_id: uuid.UUID
    chunks_used: List[KBSearchResult]
    retrieval_time_ms: int
    embedding_cost: float


class ChatCompletionWithKB(BaseModel):
    """Extension of chat completion request to include knowledge base."""
    knowledge_base: Optional[str] = None  # KB name or ID