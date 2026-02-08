"""Tests for the /api/providers endpoints."""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import (
    AWS_CREDENTIALS,
    AZURE_CREDENTIALS,
    GCP_CREDENTIALS,
    create_provider,
)


@pytest.mark.asyncio
async def test_list_providers_empty(client: AsyncClient):
    resp = await client.get("/api/providers/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_connect_aws_provider(client: AsyncClient):
    data = await create_provider(client, "aws")
    assert data["provider_type"] == "aws"
    assert data["status"] == "active"
    assert data["name"] == "AWS Bedrock"
    assert data["model_count"] == 12


@pytest.mark.asyncio
async def test_connect_azure_provider(client: AsyncClient):
    data = await create_provider(client, "azure")
    assert data["provider_type"] == "azure"
    assert data["status"] == "active"
    assert data["name"] == "Azure OpenAI"
    assert data["model_count"] == 8


@pytest.mark.asyncio
async def test_connect_gcp_provider(client: AsyncClient):
    data = await create_provider(client, "gcp")
    assert data["provider_type"] == "gcp"
    assert data["status"] == "active"
    assert data["name"] == "GCP Vertex AI"
    assert data["model_count"] == 7


@pytest.mark.asyncio
async def test_connect_invalid_provider_type(client: AsyncClient):
    resp = await client.post("/api/providers/connect", json={
        "provider_type": "invalid_cloud",
        "credentials": {"key": "value"},
    })
    assert resp.status_code == 422  # Pydantic enum validation


@pytest.mark.asyncio
async def test_connect_missing_required_fields(client: AsyncClient):
    resp = await client.post("/api/providers/connect", json={
        "provider_type": "aws",
        "credentials": {"access_key_id": "short", "secret_access_key": "short", "region": "us-east-1"},
    })
    assert resp.status_code == 422  # access_key_id too short


@pytest.mark.asyncio
async def test_connect_aws_missing_secret_key(client: AsyncClient):
    resp = await client.post("/api/providers/connect", json={
        "provider_type": "aws",
        "credentials": {"access_key_id": "AKIAIOSFODNN7EXAMPLE", "region": "us-east-1"},
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_connect_azure_missing_field(client: AsyncClient):
    incomplete = {k: v for k, v in AZURE_CREDENTIALS.items() if k != "subscription_id"}
    resp = await client.post("/api/providers/connect", json={
        "provider_type": "azure",
        "credentials": incomplete,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_connect_gcp_missing_project_id(client: AsyncClient):
    resp = await client.post("/api/providers/connect", json={
        "provider_type": "gcp",
        "credentials": {"service_account_json": '{"type":"service_account"}'},
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_provider_by_id(client: AsyncClient):
    created = await create_provider(client, "aws")
    provider_id = created["id"]

    resp = await client.get(f"/api/providers/{provider_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == provider_id
    assert data["provider_type"] == "aws"
    assert data["connection_health"] == "healthy"
    assert len(data["models"]) == 12


@pytest.mark.asyncio
async def test_get_provider_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/providers/{fake_id}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Provider not found"


@pytest.mark.asyncio
async def test_get_provider_models(client: AsyncClient):
    created = await create_provider(client, "azure")
    provider_id = created["id"]

    resp = await client.get(f"/api/providers/{provider_id}/models")
    assert resp.status_code == 200
    models = resp.json()
    assert len(models) == 8
    # Verify model structure
    model = models[0]
    assert "name" in model
    assert "capabilities" in model
    assert "context_window" in model
    assert "pricing_tier" in model


@pytest.mark.asyncio
async def test_verify_provider(client: AsyncClient):
    created = await create_provider(client, "aws")
    provider_id = created["id"]

    resp = await client.post(f"/api/providers/{provider_id}/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert "success" in data
    assert "message" in data
    assert "latency_ms" in data
    assert isinstance(data["latency_ms"], (int, float))


@pytest.mark.asyncio
async def test_delete_provider(client: AsyncClient):
    created = await create_provider(client, "gcp")
    provider_id = created["id"]

    resp = await client.delete(f"/api/providers/{provider_id}")
    assert resp.status_code == 204

    # Confirm deleted
    resp = await client.get(f"/api/providers/{provider_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_provider_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/api/providers/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_multiple_providers_listed(client: AsyncClient):
    await create_provider(client, "aws")
    await create_provider(client, "azure")
    await create_provider(client, "gcp")

    resp = await client.get("/api/providers/")
    assert resp.status_code == 200
    providers = resp.json()
    assert len(providers) == 3
    types = {p["provider_type"] for p in providers}
    assert types == {"aws", "azure", "gcp"}


@pytest.mark.asyncio
async def test_duplicate_provider_allowed(client: AsyncClient):
    """The API allows connecting the same provider type multiple times."""
    await create_provider(client, "aws")
    await create_provider(client, "aws")

    resp = await client.get("/api/providers/")
    providers = resp.json()
    aws_providers = [p for p in providers if p["provider_type"] == "aws"]
    assert len(aws_providers) == 2
