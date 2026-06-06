"""
Origami knowledge ingestion pipeline (Phase 0).

Extracts content from three sources into a unified `IngestionRecord` stream:

- Internal markdown docs (CLAUDE.md, ARCHITECTURAL_PATTERNS.md, docs/*.md)
- The live FastAPI OpenAPI spec (one record per endpoint)
- The Typer CLI command tree (one record per command)

Downstream (Phase 1) will embed and write these into the `bonito-knowledge`
internal KB. This module only handles extraction — no DB or vector-store writes.
"""

from .models import IngestionRecord, SourceType

__all__ = ["IngestionRecord", "SourceType"]
