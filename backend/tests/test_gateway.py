"""Tests for the gateway endpoints (/v1/* and /api/gateway/*)."""

import uuid
import hashlib
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import AsyncClient

from app.services.gateway import generate_api_key, hash_api_key, PolicyViolation, _generate_model_aliases


class TestModelAliases:
    """Tests for model alias generation."""

    def test_gcp_version_suffix(self):
        aliases = _generate_model_aliases("gemini-2.0-flash-001")
        assert "gemini-2.0-flash" in aliases

    def test_gcp_lite_version_suffix(self):
        aliases = _generate_model_aliases("gemini-2.0-flash-lite-001")
        assert "gemini-2.0-flash-lite" in aliases

    def test_azure_date_suffix(self):
        aliases = _generate_model_aliases("gpt-4o-mini-2024-07-18")
        assert "gpt-4o-mini" in aliases

    def test_gcp_preview_suffix(self):
        aliases = _generate_model_aliases("gemini-2.5-flash-preview-04-17")
        assert "gemini-2.5-flash" in aliases

    def test_no_alias_for_stable_names(self):
        # These are already short/stable - no aliases needed
        assert _generate_model_aliases("gemini-2.5-flash") == []
        assert _generate_model_aliases("gemini-2.5-pro") == []

    def test_aws_models_stable(self):
        # AWS model IDs don't match any suffix patterns
        assert _generate_model_aliases("amazon.nova-lite-v1:0") == []
        assert _generate_model_aliases("amazon.nova-pro-v1:0") == []
        assert _generate_model_aliases("anthropic.claude-sonnet-4-20250514-v1:0") == []

    def test_no_self_alias(self):
        # Canonical name should never appear in its own alias list
        for model in [
            "gemini-2.0-flash-001",
            "gpt-4o-mini-2024-07-18",
            "amazon.nova-lite-v1:0",
        ]:
            aliases = _generate_model_aliases(model)
            assert model not in aliases

    def test_openai_date_models(self):
        aliases = _generate_model_aliases("gpt-4o-2024-11-20")
        assert "gpt-4o" in aliases

    def test_multiple_aliases(self):
        # A model with both preview and date patterns should generate multiple aliases
        aliases = _generate_model_aliases("gemini-2.5-flash-preview-04-17")
        assert "gemini-2.5-flash" in aliases  # stripped preview entirely


class TestGatewayKeyManagement:
    """Tests for /api/gateway/keys endpoints (JWT-authenticated)."""

    @pytest.mark.asyncio
    async def test_list_keys_empty(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/gateway/keys", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_key(self, client: AsyncClient, auth_headers):
        resp = await client.post("/api/gateway/keys", headers=auth_headers, json={
            "name": "Test Key",
            "rate_limit": 100,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Key"
        assert data["rate_limit"] == 100
        assert data["key"].startswith("bn-")
        assert data["key_prefix"].startswith("bn-")
        assert data["key_prefix"].endswith("...")

    @pytest.mark.asyncio
    async def test_create_key_with_allowed_models(self, client: AsyncClient, auth_headers):
        resp = await client.post("/api/gateway/keys", headers=auth_headers, json={
            "name": "Restricted Key",
            "allowed_models": {"models": ["gpt-4o", "claude-3-5-sonnet"], "providers": ["aws"]},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["allowed_models"] is not None
        assert data["allowed_models"]["models"] == ["gpt-4o", "claude-3-5-sonnet"]

    @pytest.mark.asyncio
    async def test_list_keys_after_creation(self, client: AsyncClient, auth_headers):
        await client.post("/api/gateway/keys", headers=auth_headers, json={
            "name": "Key Alpha",
        })
        await client.post("/api/gateway/keys", headers=auth_headers, json={
            "name": "Key Beta",
        })
        resp = await client.get("/api/gateway/keys", headers=auth_headers)
        assert resp.status_code == 200
        keys = resp.json()
        assert len(keys) == 2
        # Keys should NOT contain the full key value in list response
        for k in keys:
            assert "key" not in k or k.get("key") is None

    @pytest.mark.asyncio
    async def test_revoke_key(self, client: AsyncClient, auth_headers):
        create_resp = await client.post("/api/gateway/keys", headers=auth_headers, json={
            "name": "Revoke Me",
        })
        key_id = create_resp.json()["id"]

        del_resp = await client.delete(f"/api/gateway/keys/{key_id}", headers=auth_headers)
        assert del_resp.status_code == 204

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_key(self, client: AsyncClient, auth_headers):
        fake_id = str(uuid.uuid4())
        resp = await client.delete(f"/api/gateway/keys/{fake_id}", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_keys_require_auth(self, client: AsyncClient):
        resp = await client.get("/api/gateway/keys")
        assert resp.status_code == 403


class TestGatewayAPIKeyHelpers:
    """Unit tests for API key generation and hashing."""

    def test_generate_api_key_format(self):
        raw, key_hash, prefix = generate_api_key()
        assert raw.startswith("bn-")
        assert len(raw) > 20
        assert prefix.endswith("...")
        assert key_hash == hashlib.sha256(raw.encode()).hexdigest()

    def test_hash_api_key_deterministic(self):
        key = "bn-abc123def456"
        h1 = hash_api_key(key)
        h2 = hash_api_key(key)
        assert h1 == h2

    def test_different_keys_different_hashes(self):
        _, h1, _ = generate_api_key()
        _, h2, _ = generate_api_key()
        assert h1 != h2


class TestModelAllowlistEnforcement:
    """Tests for policy enforcement in gateway service."""

    @pytest.mark.asyncio
    async def test_unrestricted_key_allows_any_model(self):
        from app.services.gateway import check_model_allowed
        from app.models.gateway import GatewayKey

        key = MagicMock(spec=GatewayKey)
        key.allowed_models = None
        # Should not raise
        await check_model_allowed(key, "gpt-4o")
        await check_model_allowed(key, "any-model-name")

    @pytest.mark.asyncio
    async def test_restricted_key_allows_listed_model(self):
        from app.services.gateway import check_model_allowed
        from app.models.gateway import GatewayKey

        key = MagicMock(spec=GatewayKey)
        key.allowed_models = {"models": ["gpt-4o", "claude-3-5-sonnet"]}
        # Should not raise
        await check_model_allowed(key, "gpt-4o")

    @pytest.mark.asyncio
    async def test_restricted_key_blocks_unlisted_model(self):
        from app.services.gateway import check_model_allowed
        from app.models.gateway import GatewayKey

        key = MagicMock(spec=GatewayKey)
        key.allowed_models = {"models": ["gpt-4o"]}
        with pytest.raises(PolicyViolation, match="not allowed"):
            await check_model_allowed(key, "forbidden-model")

    @pytest.mark.asyncio
    async def test_model_access_policy_blocks_unapproved_model(self):
        from app.services.gateway import check_model_access_policy

        mock_db = AsyncMock()
        mock_policy = MagicMock()
        mock_policy.name = "Model Restrict"
        mock_policy.rules_json = {"allowed_models": ["gpt-4o"]}
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_policy
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(PolicyViolation, match="not approved"):
            await check_model_access_policy(mock_db, uuid.uuid4(), "unapproved-model")

    @pytest.mark.asyncio
    async def test_no_model_access_policy_allows_all(self):
        from app.services.gateway import check_model_access_policy

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # no policy
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Should not raise
        await check_model_access_policy(mock_db, uuid.uuid4(), "anything")


class TestGatewayChat:
    """Tests for the /v1/chat/completions endpoint."""

    @pytest.mark.asyncio
    async def test_chat_requires_api_key(self, client: AsyncClient):
        resp = await client.post("/v1/chat/completions", json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Hello"}],
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_rejects_invalid_key_format(self, client: AsyncClient):
        resp = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer not-a-bn-key"},
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        assert resp.status_code == 401
        assert "Invalid API key format" in resp.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_chat_rejects_unknown_key(self, client: AsyncClient):
        resp = await client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer bn-deadbeef12345678"},
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        assert resp.status_code == 401
        assert "Invalid or revoked" in resp.json()["error"]["message"]


class TestGatewayConfig:
    """Tests for /api/gateway/config endpoints."""

    @pytest.mark.asyncio
    async def test_get_config_creates_default(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/gateway/config", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["routing_strategy"] == "cost-optimized"
        assert data["default_rate_limit"] == 60
        assert data["cost_tracking_enabled"] is True

    @pytest.mark.asyncio
    async def test_update_config(self, client: AsyncClient, auth_headers):
        # First get to ensure config exists
        await client.get("/api/gateway/config", headers=auth_headers)

        resp = await client.put("/api/gateway/config", headers=auth_headers, json={
            "routing_strategy": "latency-optimized",
            "default_rate_limit": 120,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["routing_strategy"] == "latency-optimized"
        assert data["default_rate_limit"] == 120


class TestGatewayUsage:
    """Tests for /api/gateway/usage endpoint."""

    @pytest.mark.asyncio
    async def test_usage_returns_structure(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/gateway/usage", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_requests" in data
        assert "total_input_tokens" in data
        assert "total_output_tokens" in data
        assert "total_cost" in data
        assert "by_model" in data
        assert "by_day" in data

    @pytest.mark.asyncio
    async def test_usage_empty_returns_zeros(self, client: AsyncClient, auth_headers):
        resp = await client.get("/api/gateway/usage", headers=auth_headers)
        data = resp.json()
        assert data["total_requests"] == 0
        assert data["total_input_tokens"] == 0
        assert data["total_output_tokens"] == 0
        assert data["total_cost"] == 0.0
