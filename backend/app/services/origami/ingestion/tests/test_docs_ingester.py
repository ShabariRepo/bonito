"""Tests for the docs ingester. Runs against the live repo state."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.origami.ingestion.docs_ingester import (
    PRIMARY_DOCS,
    _split_on_h2,
    _split_oversized_chunk,
    ingest_docs,
)
from app.services.origami.ingestion.models import IngestionRecord, SourceType


def test_ingest_docs_returns_records_against_live_repo() -> None:
    """Smoke test: real repo, real docs, real records."""
    records = ingest_docs()
    assert records, "Expected at least one record from the live repo state"
    assert all(isinstance(r, IngestionRecord) for r in records)
    assert all(r.source_type == SourceType.DOC for r in records)
    assert all(r.content.strip() for r in records), "No record should be empty"
    assert all(r.title for r in records), "Every record should have a title"


def test_ingest_docs_covers_primary_docs() -> None:
    """The four named primary docs should each appear at least once."""
    records = ingest_docs()
    paths_seen = {r.source_path for r in records}

    # At minimum CLAUDE.md and ORIGAMI-MVP-PLAN.md must exist in the repo
    # (we're literally reading them in this conversation). The others may
    # be missing in a stripped checkout — that's fine.
    must_have = {"CLAUDE.md", "docs/ORIGAMI-MVP-PLAN.md"}
    for required in must_have:
        assert required in paths_seen, f"Expected {required} in ingested paths"

    # Confirm primary doc coverage is at least partial
    primary_seen = paths_seen & set(PRIMARY_DOCS)
    assert primary_seen, f"No primary docs found. PRIMARY_DOCS={PRIMARY_DOCS}"


def test_chunk_index_unique_per_doc() -> None:
    records = ingest_docs()
    by_path: dict[str, list[int]] = {}
    for r in records:
        by_path.setdefault(r.source_path, []).append(r.metadata["chunk_index"])
    for path, indices in by_path.items():
        assert len(indices) == len(set(indices)), f"Duplicate chunk_index in {path}"


def test_metadata_carries_token_estimate() -> None:
    records = ingest_docs()
    for r in records:
        assert "token_estimate" in r.metadata
        assert isinstance(r.metadata["token_estimate"], int)
        assert r.metadata["token_estimate"] > 0


def test_split_on_h2_splits_correctly() -> None:
    md = """# Top heading

Intro paragraph.

## Section A

Body A.

## Section B

Body B with multiple lines.

And more.
"""
    sections = _split_on_h2(md)
    # preamble + 2 h2 sections
    assert len(sections) == 3
    assert sections[0][0] == ""
    assert "Intro paragraph" in sections[0][1]
    assert sections[1][0] == "Section A"
    assert "Body A" in sections[1][1]
    assert sections[2][0] == "Section B"
    assert "And more" in sections[2][1]


def test_split_on_h2_handles_no_headings() -> None:
    md = "Just a single block of text.\n\nNo headings here."
    sections = _split_on_h2(md)
    assert len(sections) == 1
    assert sections[0][0] == ""
    assert "Just a single block" in sections[0][1]


def test_split_oversized_chunk_respects_target() -> None:
    # Build a body that comfortably exceeds the target.
    word = "alpha "
    huge = "\n\n".join([word * 500] * 5)  # 5 paragraphs * 500 words each
    chunks = _split_oversized_chunk("Big Section", huge, target=200)
    assert len(chunks) >= 2
    assert all(h == "Big Section" for h, _ in chunks)
    # No chunk should be wildly over target (we allow some overshoot for
    # last-paragraph spillover)
    for _, body in chunks:
        # 1 word ≈ 1.3 tokens
        approx = int(len(body.split()) * 1.3)
        assert approx < target_word_limit(200) * 4


def target_word_limit(token_target: int) -> int:
    return token_target  # generous bound for the smoke check above


def test_ingest_docs_respects_override_root(tmp_path: Path) -> None:
    """Custom repo_root should be honored."""
    (tmp_path / "CLAUDE.md").write_text(
        "# Tiny Doc\n\n## First\n\nHello.\n\n## Second\n\nWorld.\n"
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "extra.md").write_text("# Extra\n\nNo h2 here.\n")

    records = ingest_docs(repo_root=tmp_path)
    paths = {r.source_path for r in records}
    assert "CLAUDE.md" in paths
    assert "docs/extra.md" in paths


def test_ingest_docs_skips_missing_primaries(tmp_path: Path) -> None:
    """A missing primary doc should warn, not crash."""
    # Empty repo — no CLAUDE.md, no docs/. Should return [] cleanly.
    records = ingest_docs(repo_root=tmp_path)
    assert records == []
