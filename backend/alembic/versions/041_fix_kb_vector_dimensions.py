"""Fix KB vector column to 1024 dims and backfill existing KBs

The vector(768) -> vector(1024) change from migration 018 may not have
applied on all environments. This migration ensures the column is
vector(1024) to match Titan Embed V2's native output, and updates any
KBs still configured with 768 dims.

Revision ID: 041_fix_kb_vector_dims
Revises: 040_backfill_email_verified
Create Date: 2026-05-25
"""
from alembic import op


revision = "041_fix_kb_vector_dims"
down_revision = "040_backfill_email_verified"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop HNSW index before altering column type
    op.execute("DROP INDEX IF EXISTS idx_kb_chunks_embedding")

    # Clear existing embeddings — pgvector can't cast between dimensions,
    # so we must NULL out any 768-dim vectors before changing to 1024.
    # Chunk text is preserved; documents will need re-processing.
    op.execute("UPDATE kb_chunks SET embedding = NULL WHERE embedding IS NOT NULL")

    # Now safe to change column type (no non-null vectors to cast)
    op.execute(
        "ALTER TABLE kb_chunks "
        "ALTER COLUMN embedding TYPE vector(1024) "
        "USING embedding::vector(1024)"
    )

    # Recreate HNSW index
    op.execute("""
        CREATE INDEX idx_kb_chunks_embedding
        ON kb_chunks USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # Backfill: update any KBs with embedding_dimensions=768 to 1024
    # (768 was the old schema default, but Titan V2 returns 1024 natively)
    op.execute(
        "UPDATE knowledge_bases SET embedding_dimensions = 1024 "
        "WHERE embedding_dimensions = 768"
    )


def downgrade() -> None:
    # Revert to 768 dims
    op.execute("DROP INDEX IF EXISTS idx_kb_chunks_embedding")
    op.execute(
        "ALTER TABLE kb_chunks "
        "ALTER COLUMN embedding TYPE vector(768) "
        "USING embedding::vector(768)"
    )
    op.execute("""
        CREATE INDEX idx_kb_chunks_embedding
        ON kb_chunks USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    op.execute(
        "UPDATE knowledge_bases SET embedding_dimensions = 768 "
        "WHERE embedding_dimensions = 1024"
    )
