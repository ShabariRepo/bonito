# Origami Ingestion Pipeline (Phase 0)

Extracts platform knowledge from three sources into a unified stream of
`IngestionRecord` objects. Downstream (Phase 1) embeds + writes these into
the internal `bonito-knowledge` KB that powers Origami.

**Scope:** extraction only. No DB writes. No vector store. No embeddings.
Those land in Phase 1.

---

## Modules

| File | Purpose | Status |
|---|---|---|
| `models.py` | `IngestionRecord` Pydantic v2 model + `SourceType` enum | Working |
| `docs_ingester.py` | Reads `CLAUDE.md`, `ARCHITECTURAL_PATTERNS.md`, `docs/*.md`. Chunks on `## ` h2 headings. | Working |
| `openapi_extractor.py` | Walks FastAPI routes via `app.openapi()`. One record per endpoint. | Working with caveats — see TODOs |
| `cli_extractor.py` | Walks the Typer command tree. One record per leaf command. Subprocess fallback for environments without `bonito_cli` importable. | Working |
| `unified_ingester.py` | Orchestrates all three. CLI entry point with summary + JSON modes. | Working |
| `tests/` | pytest tests against the live repo state. | Working |

---

## How to invoke

### From Python

```python
from app.services.origami.ingestion import (
    ingest_docs,
    extract_from_app,
    extract_cli,
    ingest_all,
    summarize,
)

records = ingest_all()
print(summarize(records))
# -> {'doc': 312, 'openapi': 184, 'cli': 76, 'total': 572}
```

Individual sources:

```python
from app.services.origami.ingestion.docs_ingester import ingest_docs
from app.services.origami.ingestion.openapi_extractor import extract_from_spec
from app.services.origami.ingestion.cli_extractor import extract_cli

doc_records = ingest_docs()
cli_records = extract_cli()

# Test-friendly: extract from a pre-built spec dict
spec = {"paths": {"/health": {"get": {"summary": "Health check", "responses": {"200": {"description": "ok"}}}}}}
api_records = extract_from_spec(spec)
```

### From the shell

The orchestrator exposes a CLI:

```bash
# Print summary
python -m app.services.origami.ingestion.unified_ingester

# Print each record as JSON (for piping into Phase 1's loader)
python -m app.services.origami.ingestion.unified_ingester --json

# Run only one source
python -m app.services.origami.ingestion.unified_ingester --source docs --source cli

# Show extractor logs
python -m app.services.origami.ingestion.unified_ingester -v
```

Run from `backend/`:

```bash
cd backend && python -m app.services.origami.ingestion.unified_ingester
```

### Tests

```bash
cd backend && pytest app/services/origami/ingestion/tests -v
```

Tests use the live repo state (real `CLAUDE.md`, real `docs/*.md`, real
Typer app, mock OpenAPI dict). They will catch regressions if the repo
layout changes underneath the extractor.

---

## What's working end-to-end

- `models.IngestionRecord` is a strict (`extra="forbid"`) Pydantic v2 model
  with a `stable_id()` for upsert dedupe in Phase 1.
- Docs ingester: reads the four primary docs + every `docs/*.md`, splits on
  `## `, further splits any section over ~1500 estimated tokens, returns
  one record per chunk. Token estimate is `words * 1.3` — accurate enough
  for sizing decisions, not for billing.
- OpenAPI extractor: `extract_from_spec(spec)` is a pure function. The live
  `extract_from_app()` tries `from app.main import fastapi_app` and falls
  back to `[]` if the import side-effects (Sentry, settings, Vault) blow
  up. Each route produces one record with method + path + summary +
  description + flattened request/response schema.
- CLI extractor: Typer introspection walks `app.registered_groups`
  recursively, pulling structured arg/option metadata off
  `OptionInfo`/`ArgumentInfo` defaults. Subprocess fallback uses
  `bonito --help` for environments where `bonito_cli` can't be imported.
- Unified ingester: runs all three, swallows + logs per-source failures,
  emits a summary count or NDJSON.

---

## TODOs (Phase 1 will iterate on these)

- **Token estimation** — replace the `words * 1.3` proxy with `tiktoken`
  or whatever tokenizer the chosen embedding model ships with. The KB
  default is GCP `text-embedding-005` (768-dim), but this is configurable
  per-KB.
- **Chunk overlap** — docs ingester currently splits cleanly on paragraph
  breaks with zero overlap. Phase 1 should add ~50-token overlap for
  context continuity (matches the rest of the KB pipeline default).
- **OpenAPI app import** — `app.main` triggers Sentry init + Vault load +
  Redis init at import time. Long-term we want a "schema-only" import
  path that skips startup side effects. Today it works fine in-process
  (because the worker has already loaded those), but offline ingestion
  jobs need a stripped-down entrypoint.
- **CLI subprocess fallback** — currently only emits one root-help record.
  A full impl should parse rich-formatted "Commands:" tables to recurse
  into subgroups and parse Arguments/Options tables of leaves.
- **Use case cookbook** — the spec lists a fourth source (curated patterns
  de-named from real customers). Not built yet — Shabari is curating the
  first 10 by hand. When ready, drop a `cookbook_ingester.py` next to
  `docs_ingester.py` and wire it into `SOURCE_RUNNERS`.
- **Tier matrix / live org state** — these are listed as KB sources in the
  spec but are pulled live per-turn (no cache), so they don't belong here.
- **Incremental ingest** — every record carries a `stable_id()`. Phase 1
  loader should use it for upsert-by-id semantics so re-running this
  pipeline is idempotent.
- **Content hashing** — add a `content_hash` field to `IngestionRecord`
  so Phase 1 can skip re-embedding unchanged chunks.

---

## Design notes

- **Why one Pydantic model for all three sources?** Because the embed +
  store layer doesn't care where text came from. Source-specific data
  goes in `metadata`. Filtering on `source_type` in pgvector queries is
  cheap.
- **Why import paths from `Path(__file__).parents[5]`?** Because this
  module is invoked from the FastAPI worker (`cwd = backend/`) AND from
  the ingestion CLI (varies). Resolving from `__file__` is the only
  cwd-independent option.
- **Why swallow failures in the orchestrator?** Phase 0 is about getting
  something into the KB. A broken extractor shouldn't black-hole the
  others. Phase 1 should expose per-source status to a dashboard.
