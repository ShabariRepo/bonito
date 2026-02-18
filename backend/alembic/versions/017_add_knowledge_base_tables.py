"""Add knowledge base tables and enable pgvector extension

Revision ID: 017_add_knowledge_base_tables
Revises: 016_fix_key_prefix_length
Create Date: 2026-02-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "017_add_knowledge_base_tables"
down_revision = "016_fix_key_prefix_length"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension (this is idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Create knowledge_bases table
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        
        # Source configuration
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_config", sa.JSON(), nullable=False, server_default="{}"),
        
        # Embedding configuration
        sa.Column("embedding_model", sa.String(length=100), nullable=False, server_default="'auto'"),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False, server_default="1536"),
        sa.Column("chunk_size", sa.Integer(), nullable=False, server_default="512"),
        sa.Column("chunk_overlap", sa.Integer(), nullable=False, server_default="50"),
        
        # Status
        sa.Column("status", sa.String(length=20), nullable=False, server_default="'pending'"),
        sa.Column("document_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_schedule", sa.String(length=50), nullable=True),
        
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        # Constraints
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.UniqueConstraint("org_id", "name", name="uq_knowledge_bases_org_name"),
        sa.PrimaryKeyConstraint("id")
    )

    # Create kb_documents table
    op.create_table(
        "kb_documents",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("knowledge_base_id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        
        # File info
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=True),
        sa.Column("file_type", sa.String(length=20), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        
        # Processing status
        sa.Column("status", sa.String(length=20), nullable=False, server_default="'pending'"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        
        # Metadata
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        # Constraints
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )

    # Create kb_chunks table (the actual searchable pieces)
    op.create_table(
        "kb_chunks",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("knowledge_base_id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        
        # Content
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=True),
        
        # Vector embedding (pgvector type)
        sa.Column("embedding", postgresql.ARRAY(sa.Float), nullable=True),  # Will be converted to vector type
        
        # Source reference (for citations)
        sa.Column("source_file", sa.String(length=500), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_section", sa.String(length=500), nullable=True),
        
        # Metadata
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        
        # Timestamp
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        # Constraints
        sa.ForeignKeyConstraint(["document_id"], ["kb_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    
    # Create indexes
    op.create_index("ix_knowledge_bases_org_id", "knowledge_bases", ["org_id"])
    op.create_index("ix_kb_documents_knowledge_base_id", "kb_documents", ["knowledge_base_id"])
    op.create_index("ix_kb_documents_org_id", "kb_documents", ["org_id"])
    op.create_index("ix_kb_chunks_knowledge_base_id", "kb_chunks", ["knowledge_base_id"])
    op.create_index("ix_kb_chunks_document_id", "kb_chunks", ["document_id"])
    op.create_index("ix_kb_chunks_org_id", "kb_chunks", ["org_id"])
    
    # Convert embedding column to vector type and create HNSW index
    op.execute("ALTER TABLE kb_chunks ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)")
    op.execute("""
        CREATE INDEX idx_kb_chunks_embedding 
        ON kb_chunks USING hnsw (embedding vector_cosine_ops) 
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    # Drop HNSW index first
    op.execute("DROP INDEX IF EXISTS idx_kb_chunks_embedding")
    
    # Drop other indexes
    op.drop_index("ix_kb_chunks_org_id", table_name="kb_chunks")
    op.drop_index("ix_kb_chunks_document_id", table_name="kb_chunks")
    op.drop_index("ix_kb_chunks_knowledge_base_id", table_name="kb_chunks")
    op.drop_index("ix_kb_documents_org_id", table_name="kb_documents")
    op.drop_index("ix_kb_documents_knowledge_base_id", table_name="kb_documents")
    op.drop_index("ix_knowledge_bases_org_id", table_name="knowledge_bases")
    
    # Drop tables (in reverse order due to foreign keys)
    op.drop_table("kb_chunks")
    op.drop_table("kb_documents")
    op.drop_table("knowledge_bases")
    
    # Note: We don't drop the pgvector extension in downgrade as it might be used elsewhere