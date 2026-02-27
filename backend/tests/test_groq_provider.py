"""Tests for Groq provider integration."""

from unittest.mock import patch, AsyncMock, MagicMock
import json

import pytest
from httpx import AsyncClient

from app.schemas.provider import ProviderType
from app.services.providers.base import CredentialInfo
from app.services.providers.groq_provider import GroqProvider, GROQ_MODELS
from app.services.provider_service import validate_credentials, MOCK_CATALOG

# Test credentials
GROQ_CREDENTIALS = {
    "api_key": "gsk_test123456789012345678901234567890123456789012345678901234567890"
}

# Patch target for validate_credentials on the provider class
_GROQ_VALIDATE = "app.services.providers.groq_provider.GroqProvider.validate_credentials"


def _valid():
    return CredentialInfo(valid=True, account_id="groq", user_id="groq_user", message="Credentials valid")


def _invalid(msg="Invalid API key"):
    return CredentialInfo(valid=False, message=msg)


async def _create(client, auth_headers, ptype, creds):
    resp = await client.post(
        "/api/providers/connect",
        headers=auth_headers,
        json={"provider_type": ptype, "credentials": creds},
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    return resp.json()


# ── ProviderType enum ──────────────────────────────────────────


def test_groq_in_provider_type_enum():
    """Groq should be a valid ProviderType."""
    assert "groq" in [e.value for e in ProviderType]
    assert ProviderType.groq == "groq"


# ── Model catalog ─────────────────────────────────────────────


def test_groq_static_model_catalog_count():
    """The static GROQ_MODELS catalog should have 11 models."""
    assert len(GROQ_MODELS) == 11


def test_groq_model_catalog_ids():
    """All expected model IDs should be present."""
    model_ids = {m["model_id"] for m in GROQ_MODELS}
    expected = {
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama-3.3-70b-specdec",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
        "deepseek-r1-distill-llama-70b",
        "qwen-2.5-coder-32b",
        "llama-3.2-1b-preview",
        "llama-3.2-3b-preview",
        "llama-3.2-11b-vision-preview",
        "llama-3.2-90b-vision-preview",
    }
    assert model_ids == expected


def test_groq_all_models_support_streaming():
    """All Groq models should support streaming."""
    for model in GROQ_MODELS:
        assert "streaming" in model["capabilities"], f"{model['model_id']} missing streaming"


def test_groq_models_have_pricing():
    """All models should have non-zero pricing."""
    for model in GROQ_MODELS:
        assert model["input_price_per_1m"] > 0, f"{model['model_id']} missing input pricing"
        assert model["output_price_per_1m"] > 0, f"{model['model_id']} missing output pricing"


def test_groq_in_mock_catalog():
    """Groq should be in the provider_service MOCK_CATALOG."""
    assert "groq" in MOCK_CATALOG
    assert len(MOCK_CATALOG["groq"]) == 11


# ── Credential validation (unit) ──────────────────────────────


def test_validate_credentials_groq_valid():
    """Valid groq credentials should pass format validation."""
    valid, error = validate_credentials("groq", GROQ_CREDENTIALS)
    assert valid is True
    assert error == ""


def test_validate_credentials_groq_missing_key():
    """Missing api_key should fail validation."""
    valid, error = validate_credentials("groq", {})
    assert valid is False
    assert "api_key" in error


def test_validate_credentials_groq_short_key():
    """Short api_key should fail validation."""
    valid, error = validate_credentials("groq", {"api_key": "short"})
    assert valid is False
    assert "too short" in error


# ── Provider class (mocked HTTP) ──────────────────────────────


@pytest.mark.asyncio
async def test_groq_provider_validate_success():
    """GroqProvider.validate_credentials should return valid on 200."""
    provider = GroqProvider(api_key="gsk_test_key_12345678901234567890")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": [{"id": "llama-3.3-70b-versatile"}]}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        result = await provider.validate_credentials()

    assert result.valid is True
    assert result.account_id == "groq"


@pytest.mark.asyncio
async def test_groq_provider_validate_invalid_key():
    """GroqProvider.validate_credentials should return invalid on 401."""
    provider = GroqProvider(api_key="gsk_bad_key_123456789012345678901")

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        result = await provider.validate_credentials()

    assert result.valid is False
    assert "Invalid API key" in result.message


@pytest.mark.asyncio
async def test_groq_provider_health_check_healthy():
    """Health check should return healthy on 200."""
    provider = GroqProvider(api_key="gsk_test_key_12345678901234567890")

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        result = await provider.health_check()

    assert result.healthy is True
    assert result.account_id == "groq"


@pytest.mark.asyncio
async def test_groq_provider_health_check_unhealthy():
    """Health check should return unhealthy on non-200."""
    provider = GroqProvider(api_key="gsk_test_key_12345678901234567890")

    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        result = await provider.health_check()

    assert result.healthy is False


@pytest.mark.asyncio
async def test_groq_provider_invoke_model():
    """invoke_model should parse OpenAI-compatible response."""
    provider = GroqProvider(api_key="gsk_test_key_12345678901234567890")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Hello from Groq!"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await provider.invoke_model(
            model_id="llama-3.3-70b-versatile",
            prompt="Hello",
            max_tokens=100,
        )

    assert result.response_text == "Hello from Groq!"
    assert result.input_tokens == 10
    assert result.output_tokens == 5
    assert result.model_id == "llama-3.3-70b-versatile"


@pytest.mark.asyncio
async def test_groq_provider_invoke_rate_limited():
    """invoke_model should raise RuntimeError on 429."""
    provider = GroqProvider(api_key="gsk_test_key_12345678901234567890")

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Rate limit exceeded"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        with pytest.raises(RuntimeError, match="Rate limited"):
            await provider.invoke_model(
                model_id="llama-3.3-70b-versatile",
                prompt="Hello",
            )


@pytest.mark.asyncio
async def test_groq_provider_list_models_static_fallback():
    """list_models should fall back to static catalog on API error."""
    provider = GroqProvider(api_key="gsk_test_key_12345678901234567890")

    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        # Also mock redis to avoid connection issues
        with patch("app.services.providers.groq_provider.redis_client") as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.setex = AsyncMock()
            models = await provider.list_models()

    assert len(models) == 11
    model_ids = {m.model_id for m in models}
    assert "llama-3.3-70b-versatile" in model_ids
    assert "deepseek-r1-distill-llama-70b" in model_ids


# ── Integration tests (connect flow) ──────────────────────────


@pytest.mark.asyncio
async def test_connect_groq_provider(client: AsyncClient, auth_headers):
    """Connecting groq should create an active provider."""
    with patch(_GROQ_VALIDATE, new_callable=AsyncMock, return_value=_valid()):
        data = await _create(client, auth_headers, "groq", GROQ_CREDENTIALS)
    assert data["provider_type"] == "groq"
    assert data["status"] == "active"
    assert data["name"] == "Groq"


@pytest.mark.asyncio
async def test_groq_invalid_key_rejected(client: AsyncClient, auth_headers):
    """Invalid groq API key should be rejected with 422."""
    with patch(_GROQ_VALIDATE, new_callable=AsyncMock, return_value=_invalid()):
        resp = await client.post(
            "/api/providers/connect",
            headers=auth_headers,
            json={"provider_type": "groq", "credentials": GROQ_CREDENTIALS},
        )
    assert resp.status_code == 422
    body = resp.json()
    detail = body.get("error", {}).get("message", "") or body.get("detail", "")
    assert "Groq credential validation failed" in detail


@pytest.mark.asyncio
async def test_groq_missing_api_key(client: AsyncClient, auth_headers):
    """Missing api_key should fail schema validation."""
    resp = await client.post(
        "/api/providers/connect",
        headers=auth_headers,
        json={"provider_type": "groq", "credentials": {}},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_groq_short_api_key(client: AsyncClient, auth_headers):
    """Short api_key should fail schema validation."""
    resp = await client.post(
        "/api/providers/connect",
        headers=auth_headers,
        json={"provider_type": "groq", "credentials": {"api_key": "short"}},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_groq_unexpected_credential_field(client: AsyncClient, auth_headers):
    """Unexpected credential fields should be rejected."""
    resp = await client.post(
        "/api/providers/connect",
        headers=auth_headers,
        json={"provider_type": "groq", "credentials": {**GROQ_CREDENTIALS, "unexpected_field": "value"}},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_groq_models_returned(client: AsyncClient, auth_headers):
    """Connected groq provider should return models."""
    with patch(_GROQ_VALIDATE, new_callable=AsyncMock, return_value=_valid()):
        data = await _create(client, auth_headers, "groq", GROQ_CREDENTIALS)

    resp = await client.get(f"/api/providers/{data['id']}/models", headers=auth_headers)
    assert resp.status_code == 200
    names = [m["name"] for m in resp.json()]
    assert "Llama 3.3 70B" in names
    assert "DeepSeek R1 Distill 70B" in names


@pytest.mark.asyncio
async def test_groq_provider_listed(client: AsyncClient, auth_headers):
    """Groq should appear in provider list."""
    with patch(_GROQ_VALIDATE, new_callable=AsyncMock, return_value=_valid()):
        await _create(client, auth_headers, "groq", GROQ_CREDENTIALS)

    resp = await client.get("/api/providers/", headers=auth_headers)
    assert resp.status_code == 200
    types = {p["provider_type"] for p in resp.json()}
    assert "groq" in types


@pytest.mark.asyncio
async def test_groq_provider_delete(client: AsyncClient, auth_headers):
    """Deleting groq provider should remove it."""
    with patch(_GROQ_VALIDATE, new_callable=AsyncMock, return_value=_valid()):
        data = await _create(client, auth_headers, "groq", GROQ_CREDENTIALS)

    resp = await client.delete(f"/api/providers/{data['id']}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get("/api/providers/", headers=auth_headers)
    assert not any(p["id"] == data["id"] for p in resp.json())
