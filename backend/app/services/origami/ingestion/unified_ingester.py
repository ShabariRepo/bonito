"""
Orchestrates all three Origami ingestion sources.

Single entry point: `ingest_all()` returns the combined `list[IngestionRecord]`.
Failures in any one source are logged + swallowed so a broken extractor
doesn't take down the whole ingestion run — Phase 1 will likely want to
surface partial-failure status to a dashboard.

CLI invocation:

    python -m app.services.origami.ingestion.unified_ingester
    python -m app.services.origami.ingestion.unified_ingester --json
    python -m app.services.origami.ingestion.unified_ingester --source docs
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from typing import Callable

from .cli_extractor import extract_cli
from .docs_ingester import ingest_docs
from .models import IngestionRecord, SourceType
from .openapi_extractor import extract_from_app

logger = logging.getLogger(__name__)


SOURCE_RUNNERS: dict[str, Callable[[], list[IngestionRecord]]] = {
    "docs": ingest_docs,
    "openapi": extract_from_app,
    "cli": extract_cli,
}


def ingest_all(sources: list[str] | None = None) -> list[IngestionRecord]:
    """
    Run every source and return the combined record list.

    Args:
        sources: Optional subset of sources to run. Defaults to all.
                 Valid values: "docs", "openapi", "cli".

    Returns:
        Combined records. Empty list if everything fails (logged loudly).
    """
    to_run = sources or list(SOURCE_RUNNERS.keys())
    combined: list[IngestionRecord] = []
    for name in to_run:
        runner = SOURCE_RUNNERS.get(name)
        if runner is None:
            logger.warning("Unknown source %r — skipping", name)
            continue
        try:
            records = runner()
        except Exception as exc:
            logger.exception("Source %r failed: %s", name, exc)
            continue
        logger.info("Source %r produced %d records", name, len(records))
        combined.extend(records)
    return combined


def summarize(records: list[IngestionRecord]) -> dict[str, int]:
    """Count by source_type. Useful for the CLI summary output."""
    counter: Counter[str] = Counter(r.source_type.value for r in records)
    return {s.value: counter.get(s.value, 0) for s in SourceType} | {"total": len(records)}


def _cli() -> int:
    parser = argparse.ArgumentParser(
        prog="origami-ingest",
        description="Run the Origami KB ingestion pipeline (Phase 0).",
    )
    parser.add_argument(
        "--source",
        action="append",
        choices=list(SOURCE_RUNNERS.keys()),
        help="Restrict to one or more sources. Repeatable. Defaults to all.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print every record as JSON (one per line) instead of a summary.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show INFO-level logs from extractors.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    records = ingest_all(args.source)
    if args.json:
        for r in records:
            sys.stdout.write(r.model_dump_json() + "\n")
        return 0

    summary = summarize(records)
    print("Origami ingestion summary:")
    for k, v in summary.items():
        print(f"  {k:>8}: {v}")
    return 0 if records else 1


if __name__ == "__main__":
    raise SystemExit(_cli())


__all__ = ["ingest_all", "summarize", "SOURCE_RUNNERS"]
