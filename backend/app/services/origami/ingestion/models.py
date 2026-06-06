"""
Pydantic models for Origami KB ingestion records.

An `IngestionRecord` is the unit of content handed to the embedding +
storage layer in Phase 1. Each record is one logical chunk that fits inside
a single embedding (target: <2k tokens — actual chunking handled by extractors).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Where this chunk came from. Drives downstream routing / filtering."""

    DOC = "doc"            # internal markdown doc
    OPENAPI = "openapi"    # FastAPI route description
    CLI = "cli"            # Typer CLI command


class IngestionRecord(BaseModel):
    """
    One chunk of content destined for the `bonito-knowledge` KB.

    Phase 1 will:
      1. embed `content` via the gateway
      2. insert into pgvector with `metadata` as filterable JSONB
      3. return citations using `title` + `source_path`
    """

    model_config = {"extra": "forbid"}

    source_type: SourceType = Field(
        ..., description="Origin of the chunk (doc / openapi / cli)."
    )
    source_path: str = Field(
        ...,
        description=(
            "Stable identifier for the source. For docs: repo-relative path. "
            "For openapi: '{METHOD} {path}'. For cli: dotted command path "
            "(e.g. 'agents.create')."
        ),
    )
    title: str = Field(
        ..., description="Human-readable title used in citations and ranking."
    )
    content: str = Field(
        ...,
        description=(
            "Searchable, embeddable text. For docs this is the chunk body. "
            "For OpenAPI it's a flattened description + schema summary. "
            "For CLI it's help text + args + options."
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Free-form structured metadata. Common keys: "
            "`token_estimate`, `chunk_index`, `total_chunks`, `heading`, "
            "`http_method`, `cli_group`, `tags`."
        ),
    )

    def stable_id(self) -> str:
        """
        Deterministic ID used for dedupe / upsert in Phase 1.

        Built from source_type + source_path + chunk_index (if present) so
        re-ingesting the same doc twice updates the same row instead of
        creating dupes.
        """
        chunk = self.metadata.get("chunk_index")
        suffix = f"#{chunk}" if chunk is not None else ""
        return f"{self.source_type.value}:{self.source_path}{suffix}"
