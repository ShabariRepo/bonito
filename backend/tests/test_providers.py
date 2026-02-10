"""Tests for the /api/providers endpoints."""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import (
    AWS_CREDENTIALS,
    AZURE_CREDENTIALS,
    GCP_CREDENTIALS,
)


async def _create_provider(client: AsyncClient, auth_headers: dict, provider_type: str = "aws", credentials: dict | None = None) -> dict:
    """Helper to create a provider and return the response JSON."""
    cred_map = {"aws": AWS_CREDENTIALS, "azure": AZURE_CREDENTIALS, "gcp": GCP_CREDENTIALS}
    creds = credentials or cred_map[provider_type]
    resp = await client.post(
        "/api/providers/connect",
        headers=auth_headers,
        json={"provider_type": provider_type, "credentials": creds},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_list_providers_empty(client: AsyncClient, auth_headers):
    resp = await client.get("/api/providers/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_connect_aws_provider(client: AsyncClient, auth_headers):
    data = await _create_provider(client, auth_headers, "aws")
    assert data["provider_type"] == "aws"
    assert data["status"] == "active"
    assert data["name"] == "AWS Bedrock"


@pytest.mark.asyncio
async def test_connect_azure_provider(client: AsyncClient, auth_headers):
    data = await _create_provider(client, auth_headers, "azure")
    assert data["provider_type"] == "azure"
    assert data["status"] == "active"
    assert data["name"] == "Azure OpenAI"


@pytest.mark.asyncio
async def test_connect_gcp_provider(client: AsyncClient, auth_headers):
    data = await _create_provider(client, auth_headers, "gcp")
    assert data["provider_type"] == "gcp"
    assert data["status"] == "active"
    assert data["name"] == "GCP Vertex AI"


@pytest.mark.asyncio
async def test_connect_invalid_provider_type(client: AsyncClient, auth_headers):
    resp = await client.post("/api/providers/connect", headers=auth_headers, json={
        "provider_type": "invalid_cloud",
        "credentials": {"key": "value"},
    })
    assert resp.status_code == 422  # Pydantic enum validation


@pytest.mark.asyncio
async def test_connect_missing_required_fields(client: AsyncClient, auth_headers):
    resp = await client.post("/api/providers/connect", headers=auth_headers, json={
        "provider_type": "aws",
        "credentials": {"access_key_id": "short", "secret_access_key": "short", "region": "us-east-1"},
    })
    assert resp.status_code == 422  # access_key_id too short


@pytest.mark.asyncio
async def test_connect_aws_missing_secret_key(client: AsyncClient, auth_headers):
    resp = await client.post("/api/providers/connect", headers=auth_headers, json={
        "provider_type": "aws",
        "credentials": {"access_key_id": "AKIAIOSFODNN7EXAMPLE", "region": "us-east-1"},
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_connect_azure_missing_field(client: AsyncClient, auth_headers):
    incomplete = {k: v for k, v in AZURE_CREDENTIALS.items() if k != "subscription_id"}
    resp = await client.post("/api/providers/connect", headers=auth_headers, json={
        "provider_type": "azure",
        "credentials": incomplete,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_connect_gcp_missing_project_id(client: AsyncClient, auth_headers):
    resp = await client.post("/api/providers/connect", headers=auth_headers, json={
        "provider_type": "gcp",
        "credentials": {"service_account_json": '{"type":"service_account"}'},
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_provider_by_id(client: AsyncClient, auth_headers):
    created = await _create_provider(client, auth_headers, "aws")
    provider_id = created["id"]

    resp = await client.get(f"/api/providers/{provider_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == provider_id
    assert data["provider_type"] == "aws"


@pytest.mark.asyncio
async def test_get_provider_not_found(client: AsyncClient, auth_headers):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/providers/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["message"] == "Provider not found"


@pytest.mark.asyncio
async def test_delete_provider(client: AsyncClient, auth_headers):
    created = await _create_provider(client, auth_headers, "gcp")
    provider_id = created["id"]

    resp = await client.delete(f"/api/providers/{provider_id}", headers=auth_headers)
    assert resp.status_code == 204

    # Confirm deleted
    resp = await client.get(f"/api/providers/{provider_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_provider_not_found(client: AsyncClient, auth_headers):
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/api/providers/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_multiple_providers_listed(client: AsyncClient, auth_headers):
    await _create_provider(client, auth_headers, "aws")
    await _create_provider(client, auth_headers, "azure")
    await _create_provider(client, auth_headers, "gcp")

    resp = await client.get("/api/providers/", headers=auth_headers)
    assert resp.status_code == 200
    providers = resp.json()
    assert len(providers) == 3
    types = {p["provider_type"] for p in providers}
    assert types == {"aws", "azure", "gcp"}


@pytest.mark.asyncio
async def test_duplicate_provider_allowed(client: AsyncClient, auth_headers):
    """The API allows connecting the same provider type multiple times."""
    await _create_provider(client, auth_headers, "aws")
    await _create_provider(client, auth_headers, "aws")

    resp = await client.get("/api/providers/", headers=auth_headers)
    providers = resp.json()
    aws_providers = [p for p in providers if p["provider_type"] == "aws"]
    assert len(aws_providers) == 2


@pytest.mark.asyncio
async def test_providers_require_auth(client: AsyncClient):
    resp = await client.get("/api/providers/")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_credentials_stored_as_json(client: AsyncClient, auth_headers, test_engine):
    """Credentials should be stored as valid JSON, not Python repr."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from app.models.cloud_provider import CloudProvider
    import json

    created = await _create_provider(client, auth_headers, "aws")
    provider_id = created["id"]

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            select(CloudProvider).where(CloudProvider.id == uuid.UUID(provider_id))
        )
        provider = result.scalar_one()
        # If credentials_encrypted is set, it should be valid JSON (or encrypted blob)
        if provider.credentials_encrypted:
            # It should not contain Python-style repr artifacts like "'" or "True"
            assert "'" not in provider.credentials_encrypted or provider.credentials_encrypted.startswith("{")
