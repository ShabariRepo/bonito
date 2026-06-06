"""
Extracts the FastAPI OpenAPI spec into KB-ingestible records.

Each route becomes one `IngestionRecord` with:
- title: "METHOD /path — summary"
- content: flattened description + request/response schema summary
- metadata: tags, method, status codes, operation_id

We support two invocation modes:

1. `extract_from_app()` — imports the live FastAPI app and calls `app.openapi()`.
   This is the production path. Beware: importing `app.main` triggers Sentry
   init and other module-level side effects, so we lazy-import inside the
   function and tolerate failures.

2. `extract_from_spec(spec_dict)` — takes a pre-built OpenAPI dict. This is
   the unit-tested path and also the fallback when the app can't be imported
   (e.g. during ingestion runs in a stripped-down container).
"""

from __future__ import annotations

import logging
from typing import Any

from .models import IngestionRecord, SourceType

logger = logging.getLogger(__name__)

# Methods we care about. OpenAPI also uses 'parameters' / 'summary' at the
# path level which we surface in metadata but don't emit records for.
_HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")


def _schema_summary(schema: dict[str, Any] | None, max_props: int = 12) -> str:
    """
    Summarize a JSONSchema dict into a few lines of human-readable text.

    Not a full pretty-printer — just enough that an embedding can grok the
    rough shape. Phase 1 may want to expand `$ref` chains; we don't here to
    keep recursion / cycles simple.
    """
    if not schema:
        return ""
    if "$ref" in schema:
        return f"ref: {schema['$ref'].split('/')[-1]}"

    schema_type = schema.get("type")
    if schema_type == "array":
        items = schema.get("items") or {}
        return f"array of {_schema_summary(items)}"
    if schema_type == "object" or "properties" in schema:
        props = schema.get("properties") or {}
        required = set(schema.get("required") or [])
        lines: list[str] = []
        for i, (name, prop) in enumerate(props.items()):
            if i >= max_props:
                lines.append(f"... ({len(props) - max_props} more fields)")
                break
            req_marker = "*" if name in required else ""
            ptype = prop.get("type") or prop.get("$ref", "").split("/")[-1] or "any"
            desc = prop.get("description", "")
            line = f"  - {name}{req_marker}: {ptype}"
            if desc:
                line += f" — {desc.strip().splitlines()[0][:120]}"
            lines.append(line)
        return "object:\n" + "\n".join(lines) if lines else "object"
    if schema_type:
        return str(schema_type)
    return ""


def _request_body_summary(operation: dict[str, Any]) -> str:
    body = operation.get("requestBody")
    if not body:
        return ""
    content = body.get("content") or {}
    json_block = content.get("application/json") or {}
    schema = json_block.get("schema")
    if not schema:
        return ""
    return f"Request body:\n{_schema_summary(schema)}"


def _responses_summary(operation: dict[str, Any]) -> str:
    responses = operation.get("responses") or {}
    if not responses:
        return ""
    lines = ["Responses:"]
    for status, resp in responses.items():
        desc = (resp.get("description") or "").strip().splitlines()
        desc_line = desc[0] if desc else ""
        content = (resp.get("content") or {}).get("application/json") or {}
        schema = content.get("schema")
        line = f"  {status}: {desc_line}"
        if schema:
            inner = _schema_summary(schema).replace("\n", "\n    ")
            if inner:
                line += f"\n    {inner}"
        lines.append(line)
    return "\n".join(lines)


def _parameters_summary(operation: dict[str, Any]) -> str:
    params = operation.get("parameters") or []
    if not params:
        return ""
    lines = ["Parameters:"]
    for p in params:
        loc = p.get("in", "?")
        name = p.get("name", "?")
        required = "*" if p.get("required") else ""
        desc = (p.get("description") or "").strip().splitlines()
        desc_line = f" — {desc[0]}" if desc else ""
        lines.append(f"  - {name}{required} ({loc}){desc_line}")
    return "\n".join(lines)


def _record_for_operation(
    path: str, method: str, operation: dict[str, Any]
) -> IngestionRecord:
    method_upper = method.upper()
    summary = operation.get("summary") or ""
    description = (operation.get("description") or "").strip()
    op_id = operation.get("operationId") or ""
    tags = operation.get("tags") or []

    title = f"{method_upper} {path}"
    if summary:
        title = f"{title} — {summary}"

    parts: list[str] = [f"{method_upper} {path}"]
    if summary:
        parts.append(f"Summary: {summary}")
    if description:
        parts.append(description)
    for fn in (_parameters_summary, _request_body_summary, _responses_summary):
        block = fn(operation)
        if block:
            parts.append(block)

    content = "\n\n".join(parts)

    return IngestionRecord(
        source_type=SourceType.OPENAPI,
        source_path=f"{method_upper} {path}",
        title=title,
        content=content,
        metadata={
            "http_method": method_upper,
            "path": path,
            "operation_id": op_id,
            "tags": tags,
            "status_codes": list((operation.get("responses") or {}).keys()),
            "has_request_body": "requestBody" in operation,
            "token_estimate": int(len(content.split()) * 1.3),
        },
    )


def extract_from_spec(spec: dict[str, Any]) -> list[IngestionRecord]:
    """
    Convert a fully-built OpenAPI dict into records.

    Pure / no side effects — easy to unit-test.
    """
    paths = (spec or {}).get("paths") or {}
    records: list[IngestionRecord] = []
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in _HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue
            try:
                records.append(_record_for_operation(path, method, operation))
            except Exception as exc:  # pragma: no cover — be defensive at the boundary
                logger.warning(
                    "Skipping %s %s due to extraction error: %s", method, path, exc
                )
    logger.info("OpenAPI extract produced %d records", len(records))
    return records


def extract_from_app() -> list[IngestionRecord]:
    """
    Live path: import the FastAPI app and call `.openapi()`.

    Wrapped in a broad try/except because `app.main` import triggers Sentry
    init, settings load, etc. — fine in a running container, fragile in an
    offline ingestion job.
    """
    # TODO: once Phase 1 wires this into a periodic background task, decide
    # whether the importer runs inside the same uvicorn worker (cheap) or as
    # a standalone job that needs DATABASE_URL et al stubbed out.
    try:
        from app.main import fastapi_app  # type: ignore[import-not-found]
    except Exception as exc:
        logger.error(
            "Could not import FastAPI app for OpenAPI extraction: %s. "
            "Fall back to extract_from_spec() with a pre-built dict.",
            exc,
        )
        return []

    try:
        spec = fastapi_app.openapi()
    except Exception as exc:  # pragma: no cover — defensive
        logger.error("fastapi_app.openapi() failed: %s", exc)
        return []

    return extract_from_spec(spec)


__all__ = ["extract_from_spec", "extract_from_app"]
