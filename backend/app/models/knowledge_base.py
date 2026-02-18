import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, DateTime, Integer, Float, ForeignKey, BigInteger, Index, Boolean, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY

from app.core.database import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Source configuration
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 's3', 'azure_blob', 'gcs', 'upload'
    source_config: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Embedding configuration
    embedding_model: Mapped[str] = mapped_column(String(100), default='auto')
    embedding_dimensions: Mapped[int] = mapped_column(Integer, default=1536)
    chunk_size: Mapped[int] = mapped_column(Integer, default=512)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=50)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default='pending')  # pending, syncing, ready, error
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_schedule: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # cron expression
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    documents: Mapped[List["KBDocument"]] = relationship("KBDocument", back_populates="knowledge_base", cascade="all, delete-orphan")
    chunks: Mapped[List["KBChunk"]] = relationship("KBChunk", back_populates="knowledge_base", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_knowledge_bases_org_id", "org_id"),
        Index("uq_knowledge_bases_org_name", "org_id", "name", unique=True),
    )


class KBDocument(Base):
    __tablename__ = "kb_documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)  # Denormalized for partitioning/indexing
    
    # File info
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # path in source storage
    file_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # pdf, docx, txt, md, html, csv, json
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA-256 for dedup/change detection
    
    # Processing status
    status: Mapped[str] = mapped_column(String(20), default='pending')  # pending, processing, ready, error
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadata (customer can add tags, categories, etc.)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase", back_populates="documents")
    chunks: Mapped[List["KBChunk"]] = relationship("KBChunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_kb_documents_knowledge_base_id", "knowledge_base_id"),
        Index("ix_kb_documents_org_id", "org_id"),
    )


class KBChunk(Base):
    __tablename__ = "kb_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kb_documents.id", ondelete="CASCADE"), nullable=False)
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(nullable=False)  # Denormalized for partitioning/indexing
    
    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # position within document
    
    # Vector embedding (pgvector type - defined as ARRAY but will be vector(1536) in DB)
    embedding: Mapped[Optional[List[float]]] = mapped_column(ARRAY(Float), nullable=True)
    
    # Source reference (for citations)
    source_file: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_section: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Metadata
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document: Mapped["KBDocument"] = relationship("KBDocument", back_populates="chunks")
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase", back_populates="chunks")

    __table_args__ = (
        Index("ix_kb_chunks_knowledge_base_id", "knowledge_base_id"),
        Index("ix_kb_chunks_document_id", "document_id"),
        Index("ix_kb_chunks_org_id", "org_id"),
        # HNSW index for embedding is created in the migration
    )