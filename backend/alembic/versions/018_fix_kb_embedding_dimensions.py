"""Fix KB embedding dimensions to support Titan Embed V2 (1024-dim)

Revision ID: 018_fix_kb_embed
Revises: 017_add_knowledge_base_tables
Create Date: 2026-02-18

The initial migration hardcoded vector(1536) for OpenAI embeddings.
Production uses Amazon Titan Embed V2 which returns 1024 dimensions.
This migration updates the column and index accordingly.
"""
from alembic import op


# revision identifiers
revision = "018_fix_kb_embed"
down_revision = "017_add_knowledge_base_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing HNSW index
    op.execute("DROP INDEX IF EXISTS idx_kb_chunks_embedding")
    
    # Alter column from vector(1536) to vector(1024)
    # Since no data exists yet, this is safe
    op.execute("ALTER TABLE kb_chunks ALTER COLUMN embedding TYPE vector(1024) USING embedding::vector(1024)")
    
    # Recreate HNSW index with new dimensions
    op.execute("""
        CREATE INDEX idx_kb_chunks_embedding 
        ON kb_chunks USING hnsw (embedding vector_cosine_ops) 
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_kb_chunks_embedding")
    op.execute("ALTER TABLE kb_chunks ALTER COLUMN embedding TYPE vector(1536) USING embedding::vector(1536)")
    op.execute("""
        CREATE INDEX idx_kb_chunks_embedding 
        ON kb_chunks USING hnsw (embedding vector_cosine_ops) 
        WITH (m = 16, ef_construction = 64)
    """)
