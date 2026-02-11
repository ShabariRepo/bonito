"""Tests for OpenAI Direct and Anthropic Direct providers."""

from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient

from app.services.providers.base import CredentialInfo

# Test credentials for direct providers
OPENAI_CREDENTIALS = {
    "api_key": "sk-test123456789012345678901234567890123456789012345678901234567890"
}

OPENAI_CREDENTIALS_WITH_ORG = {
    "api_key": "sk-test123456789012345678901234567890123456789012345678901234567890",
    "organization_id": "org-test123456789012345678"
}

ANTHROPIC_CREDENTIALS = {
    "api_key": "sk-ant-api03-test123456789012345678901234567890123456789012345678901234567890"
}


def _valid():
    return CredentialInfo(valid=True, account_id="test_user", user_id="test_user", message="Credentials valid")


def _invalid(msg="Invalid API key"):
    return CredentialInfo(valid=False, message=msg)


# Patch target for validate_credentials on each provider class
_OPENAI_VALIDATE = "app.services.providers.openai_direct.OpenAIDirectProvider.validate_credentials"
_ANTHROPIC_VALIDATE = "app.services.providers.anthropic_direct.AnthropicDirectProvider.validate_credentials"


async def _create(client, auth_headers, ptype, creds):
    resp = await client.post(
        "/api/providers/connect",
        headers=auth_headers,
        json={"provider_type": ptype, "credentials": creds},
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    return resp.json()


# ── Connect ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_connect_openai_provider(client: AsyncClient, auth_headers):
    with patch(_OPENAI_VALIDATE, new_callable=AsyncMock, return_value=_valid()):
        data = await _create(client, auth_headers, "openai", OPENAI_CREDENTIALS)
    assert data["provider_type"] == "openai"
    assert data["status"] == "active"
    assert data["name"] == "OpenAI Direct"


@pytest.mark.asyncio
async def test_connect_anthropic_provider(client: AsyncClient, auth_headers):
    with patch(_ANTHROPIC_VALIDATE, new_callable=AsyncMock, return_value=_valid()):
        data = await _create(client, auth_headers, "anthropic", ANTHROPIC_CREDENTIALS)
    assert data["provider_type"] == "anthropic"
    assert data["status"] == "active"
    assert data["name"] == "Anthropic Direct"


# ── Invalid key rejection ──────────────────────────────────────


@pytest.mark.asyncio
async def test_openai_invalid_key_rejected(client: AsyncClient, auth_headers):
    with patch(_OPENAI_VALIDATE, new_callable=AsyncMock, return_value=_invalid()):
        resp = await client.post(
            "/api/providers/connect",
            headers=auth_headers,
            json={"provider_type": "openai", "credentials": OPENAI_CREDENTIALS},
        )
    assert resp.status_code == 422
    body = resp.json()
    assert "OpenAI credential validation failed" in body.get("error", {}).get("message", "") or "OpenAI credential validation failed" in body.get("detail", "")


@pytest.mark.asyncio
async def test_anthropic_invalid_key_rejected(client: AsyncClient, auth_headers):
    with patch(_ANTHROPIC_VALIDATE, new_callable=AsyncMock, return_value=_invalid()):
        resp = await client.post(
            "/api/providers/connect",
            headers=auth_headers,
            json={"provider_type": "anthropic", "credentials": ANTHROPIC_CREDENTIALS},
        )
    assert resp.status_code == 422
    body = resp.json()
    assert "Anthropic credential validation failed" in body.get("error", {}).get("message", "") or "Anthropic credential validation failed" in body.get("detail", "")


# ── Schema validation ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_openai_missing_api_key(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/providers/connect",
        headers=auth_headers,
        json={"provider_type": "openai", "credentials": {}},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_anthropic_missing_api_key(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/providers/connect",
        headers=auth_headers,
        json={"provider_type": "anthropic", "credentials": {}},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_openai_short_api_key(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/providers/connect",
        headers=auth_headers,
        json={"provider_type": "openai", "credentials": {"api_key": "short"}},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_anthropic_short_api_key(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/providers/connect",
        headers=auth_headers,
        json={"provider_type": "anthropic", "credentials": {"api_key": "short"}},
    )
    assert resp.status_code == 422


# ── Model listing ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_openai_models_returned(client: AsyncClient, auth_headers):
    with patch(_OPENAI_VALIDATE, new_callable=AsyncMock, return_value=_valid()):
        data = await _create(client, auth_headers, "openai", OPENAI_CREDENTIALS)

    resp = await client.get(f"/api/providers/{data['id']}/models", headers=auth_headers)
    assert resp.status_code == 200
    names = [m["name"] for m in resp.json()]
    assert "GPT-4o" in names
    assert "GPT-4o Mini" in names


@pytest.mark.asyncio
async def test_anthropic_models_returned(client: AsyncClient, auth_headers):
    with patch(_ANTHROPIC_VALIDATE, new_callable=AsyncMock, return_value=_valid()):
        data = await _create(client, auth_headers, "anthropic", ANTHROPIC_CREDENTIALS)

    resp = await client.get(f"/api/providers/{data['id']}/models", headers=auth_headers)
    assert resp.status_code == 200
    names = [m["name"] for m in resp.json()]
    assert "Claude 3.5 Sonnet" in names
    assert "Claude 3.5 Haiku" in names


# ── CRUD ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_direct_providers_listed_with_cloud_providers(client: AsyncClient, auth_headers):
    with patch(_OPENAI_VALIDATE, new_callable=AsyncMock, return_value=_valid()):
        await _create(client, auth_headers, "openai", OPENAI_CREDENTIALS)
    with patch(_ANTHROPIC_VALIDATE, new_callable=AsyncMock, return_value=_valid()):
        await _create(client, auth_headers, "anthropic", ANTHROPIC_CREDENTIALS)

    resp = await client.get("/api/providers/", headers=auth_headers)
    assert resp.status_code == 200
    types = {p["provider_type"] for p in resp.json()}
    assert "openai" in types
    assert "anthropic" in types


@pytest.mark.asyncio
async def test_direct_provider_delete(client: AsyncClient, auth_headers):
    with patch(_OPENAI_VALIDATE, new_callable=AsyncMock, return_value=_valid()):
        data = await _create(client, auth_headers, "openai", OPENAI_CREDENTIALS)

    resp = await client.delete(f"/api/providers/{data['id']}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get("/api/providers/", headers=auth_headers)
    assert not any(p["id"] == data["id"] for p in resp.json())


@pytest.mark.asyncio
async def test_openai_with_organization_id(client: AsyncClient, auth_headers):
    with patch(_OPENAI_VALIDATE, new_callable=AsyncMock, return_value=_valid()):
        data = await _create(client, auth_headers, "openai", OPENAI_CREDENTIALS_WITH_ORG)
    assert data["provider_type"] == "openai"
    assert data["status"] == "active"


# ── Unexpected fields ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_openai_unexpected_credential_field(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/providers/connect",
        headers=auth_headers,
        json={"provider_type": "openai", "credentials": {**OPENAI_CREDENTIALS, "unexpected_field": "value"}},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_anthropic_unexpected_credential_field(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/providers/connect",
        headers=auth_headers,
        json={"provider_type": "anthropic", "credentials": {**ANTHROPIC_CREDENTIALS, "unexpected_field": "value"}},
    )
    assert resp.status_code == 422
