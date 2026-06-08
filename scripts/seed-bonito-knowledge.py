#!/usr/bin/env python3
"""seed-bonito-knowledge.py — seed the PLATFORM-SHARED bonito-knowledge KB.

Origami uses a single platform-wide bonito-knowledge KB that all orgs
read from. This script runs the docs / OpenAPI / CLI extractors and
writes the IngestionRecords as pending KBDocuments into that one KB.

Run ONCE per docs revision (not per-org). Idempotent: re-running on the
same docs version only inserts new records.

Run from the repo root with the host Python (NOT inside the container):

    cd /Users/appa/Desktop/code/bonito
    BACKEND_DB_URL=postgresql+asyncpg://bonito:bonito@localhost:5433/bonito \\
        PYTHONPATH=backend python scripts/seed-bonito-knowledge.py

The reason: the docs extractor walks the repo (CLAUDE.md,
ARCHITECTURAL_PATTERNS.md, docs/*.md). The container only has `backend/`
mounted, so running this inside docker would extract zero docs.

For production: bake the docs into the container image at build time
(COPY CLAUDE.md docs/ /app/repo-root/) and adjust _REPO_ROOT in the
docs_ingester to honor a BONITO_REPO_ROOT env var. Then run inside the
container on a schedule (after docs deploys).
"""

from __future__ import annotations

import argparse
import asyncio
import sys


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--source",
        action="append",
        choices=["docs", "openapi", "cli"],
        help="Which extractors to run (default: all three). Repeatable.",
    )
    args = ap.parse_args()

    from app.core.database import async_session
    from app.services.origami.bonito_knowledge import seed_platform_knowledge

    async with async_session() as db:
        summary = await seed_platform_knowledge(db, sources=args.source)

    print(f"\nSeeded platform-shared bonito-knowledge KB")
    print(f"  platform_org_id:   {summary['platform_org_id']}")
    print(f"  kb_id:             {summary['kb_id']}")
    print(f"  extracted counts:  {summary['extracted']}")
    print(f"  documents written: {summary['written']}")
    print(f"  skipped (existing): {summary['skipped_existing']}")
    print("\nThe existing kb_ingestion pipeline will pick up the pending")
    print("documents and embed them. After embedding completes, Origami")
    print("for ALL orgs will start using this content as RAG context.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
