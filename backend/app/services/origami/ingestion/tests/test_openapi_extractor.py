"""
Tests for the OpenAPI extractor.

We mainly test `extract_from_spec` (pure, deterministic). `extract_from_app`
is a thin wrapper that imports the live FastAPI app — we don't run it in
unit tests because it triggers Sentry / Vault / Redis init.
"""

from __future__ import annotations

import pytest

from app.services.origami.ingestion.models import IngestionRecord, SourceType
from app.services.origami.ingestion.openapi_extractor import (
    extract_from_spec,
)


@pytest.fixture
def sample_spec() -> dict:
    return {
        "openapi": "3.0.0",
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health check",
                    "description": "Returns 200 if the service is up.",
                    "operationId": "health_check",
                    "tags": ["system"],
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/agents": {
                "post": {
                    "summary": "Create an agent",
                    "description": "Creates a new Bonobot.",
                    "operationId": "create_agent",
                    "tags": ["agents"],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name"],
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "Agent display name",
                                        },
                                        "model_id": {"type": "string"},
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {"description": "Created"},
                        "422": {"description": "Validation error"},
                    },
                },
                "get": {
                    "summary": "List agents",
                    "tags": ["agents"],
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "description": "Max rows to return",
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                },
            },
        },
    }


def test_extract_from_spec_emits_one_record_per_operation(sample_spec) -> None:
    records = extract_from_spec(sample_spec)
    # 1 GET /health + 1 POST /api/agents + 1 GET /api/agents = 3
    assert len(records) == 3
    assert all(isinstance(r, IngestionRecord) for r in records)
    assert all(r.source_type == SourceType.OPENAPI for r in records)


def test_extract_records_carry_method_and_path(sample_spec) -> None:
    records = extract_from_spec(sample_spec)
    by_path = {r.source_path: r for r in records}
    assert "GET /health" in by_path
    assert "POST /api/agents" in by_path
    assert "GET /api/agents" in by_path

    health = by_path["GET /health"]
    assert health.metadata["http_method"] == "GET"
    assert health.metadata["path"] == "/health"
    assert health.metadata["operation_id"] == "health_check"
    assert health.metadata["tags"] == ["system"]


def test_extract_includes_request_body_summary(sample_spec) -> None:
    records = extract_from_spec(sample_spec)
    create = next(r for r in records if r.source_path == "POST /api/agents")
    assert "Request body" in create.content
    assert "name" in create.content
    # name is required → should have the asterisk marker
    assert "name*" in create.content


def test_extract_includes_parameters(sample_spec) -> None:
    records = extract_from_spec(sample_spec)
    listing = next(r for r in records if r.source_path == "GET /api/agents")
    assert "Parameters" in listing.content
    assert "limit" in listing.content


def test_extract_handles_empty_spec() -> None:
    assert extract_from_spec({}) == []
    assert extract_from_spec({"paths": {}}) == []


def test_extract_ignores_non_http_methods() -> None:
    spec = {
        "paths": {
            "/foo": {
                "parameters": [],  # path-level metadata, not an operation
                "summary": "Shared summary",
                "get": {"summary": "Get foo", "responses": {"200": {"description": "ok"}}},
            }
        }
    }
    records = extract_from_spec(spec)
    assert len(records) == 1
    assert records[0].metadata["http_method"] == "GET"


def test_extract_records_have_token_estimate(sample_spec) -> None:
    for r in extract_from_spec(sample_spec):
        assert r.metadata["token_estimate"] > 0


def test_stable_id_for_openapi_record(sample_spec) -> None:
    records = extract_from_spec(sample_spec)
    ids = {r.stable_id() for r in records}
    # 3 ops → 3 distinct stable IDs
    assert len(ids) == len(records)
