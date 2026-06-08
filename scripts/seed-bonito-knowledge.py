#!/usr/bin/env python3
"""seed-bonito-knowledge.py — seed the bonito-knowledge KB for an org.

Origami's Phase 0 ingestion pipeline extracts platform docs / OpenAPI /
CLI help into IngestionRecords. This script writes those records into
the per-org `bonito-knowledge` KB as pending KBDocuments. The existing
ingestion pipeline then picks them up and embeds them.

After seeding, Origami's orchestrator will automatically retrieve top-K
matching chunks on every turn (see bonito_knowledge.retrieve_context_for_query)
and inject them into the model's context. That's how the chat can answer
"how does Bonito work" questions instead of just manipulating state.

Run from the repo root with the host Python (NOT inside the container):

    cd /Users/appa/Desktop/code/bonito
    BACKEND_DB_URL=postgresql+asyncpg://bonito:bonito@localhost:5433/bonito \\
        PYTHONPATH=backend python scripts/seed-bonito-knowledge.py --org-id <uuid>

The reason: the docs extractor walks the repo (CLAUDE.md, ARCHITECTURAL_PATTERNS.md,
docs/*.md). The container only has `backend/` mounted, so running this inside
docker would extract zero docs. Host Python has the whole repo on disk.

For production: bake the docs into the container image at build time
(COPY CLAUDE.md docs/ /app/repo-root/) and adjust _REPO_ROOT in the
docs_ingester to honor a BONITO_REPO_ROOT env var. Then run inside the
container on a schedule.

Idempotent. Re-running on the same org only inserts new records;
existing records (matched by stable_id stored as file_name) are skipped.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--org-id", required=True, help="UUID of the target organization")
    ap.add_argument(
        "--source",
        action="append",
        choices=["docs", "openapi", "cli"],
        help="Which extractors to run (default: all three). Repeatable.",
    )
    args = ap.parse_args()

    try:
        org_id = uuid.UUID(args.org_id)
    except ValueError:
        print(f"error: --org-id must be a valid UUID (got {args.org_id!r})", file=sys.stderr)
        return 2

    from app.core.database import async_session
    from app.services.origami.bonito_knowledge import seed_for_org

    async with async_session() as db:
        summary = await seed_for_org(db, org_id, sources=args.source)

    print(f"\nSeeded bonito-knowledge for org {org_id}")
    print(f"  kb_id:             {summary['kb_id']}")
    print(f"  extracted counts:  {summary['extracted']}")
    print(f"  documents written: {summary['written']}")
    print(f"  skipped (existing): {summary['skipped_existing']}")
    print("\nThe existing kb_ingestion pipeline will pick up the pending")
    print("documents and embed them. Watch the KB status in the UI.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
