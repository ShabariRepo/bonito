"""
Tests for the CLI extractor. Runs against the live `bonito_cli.app` Typer tree.

Falls back gracefully if `bonito_cli` isn't importable (CI environments without
the CLI dep installed) — those tests are skipped instead of failing.
"""

from __future__ import annotations

import pytest

from app.services.origami.ingestion.cli_extractor import (
    _import_cli_app,
    extract_cli,
    extract_from_typer,
)
from app.services.origami.ingestion.models import IngestionRecord, SourceType


def _cli_importable() -> bool:
    return _import_cli_app() is not None


pytestmark = pytest.mark.skipif(
    not _cli_importable(),
    reason="bonito_cli not importable in this environment",
)


def test_extract_from_typer_returns_records() -> None:
    records = extract_from_typer()
    assert records, "Expected non-empty list from live Typer introspection"
    assert all(isinstance(r, IngestionRecord) for r in records)
    assert all(r.source_type == SourceType.CLI for r in records)


def test_extract_records_have_required_fields() -> None:
    records = extract_from_typer()
    for r in records:
        assert r.title
        assert r.source_path
        assert r.content
        assert r.metadata.get("extraction_method") == "typer_introspection"


def test_extract_covers_known_command_groups() -> None:
    """Spot-check that key groups (agents, providers, kb) appear."""
    records = extract_from_typer()
    groups = {
        r.metadata.get("cli_group")
        for r in records
        if r.metadata.get("cli_group")
    }
    # The CLI registers ~26 groups; we expect at least these landmarks
    for expected in ("agents", "providers", "kb"):
        assert any(g and g.startswith(expected) for g in groups), (
            f"Expected at least one command under group {expected!r} — "
            f"found groups: {sorted(g for g in groups if g)[:20]}"
        )


def test_extract_records_have_dotted_source_path() -> None:
    records = extract_from_typer()
    for r in records:
        # Dotted path like "agents.create" or "auth.login"
        assert "." in r.source_path or r.source_path == "?", (
            f"Expected dotted source_path, got {r.source_path!r}"
        )


def test_extract_records_carry_args_and_options_metadata() -> None:
    records = extract_from_typer()
    has_args = any(r.metadata.get("args") for r in records)
    has_options = any(r.metadata.get("options") for r in records)
    assert has_args or has_options, (
        "Expected at least one CLI command to have args or options"
    )


def test_extract_cli_falls_back_gracefully() -> None:
    """`extract_cli()` should return non-empty if introspection works."""
    records = extract_cli()
    assert records, "Expected extract_cli() to return records in this env"
    # Every record should be a valid IngestionRecord
    for r in records:
        assert isinstance(r, IngestionRecord)
        assert r.source_type == SourceType.CLI


def test_stable_id_uniqueness() -> None:
    records = extract_from_typer()
    ids = [r.stable_id() for r in records]
    # Some leaf commands across groups may share names (e.g. `list`), but
    # the dotted path includes the group so IDs must still be unique.
    assert len(ids) == len(set(ids)), "Stable IDs collided across CLI commands"
