"""
Tests for platform-level embedding fallback.

When an org has no embedding-capable provider (e.g., only Groq or Anthropic),
EmbeddingGenerator should fall back to the platform OpenAI key if configured.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.kb_ingestion import EmbeddingGenerator


@pytest.mark.regression
class TestPlatformEmbeddingFallback:
    """Test the platform embedding key fallback in EmbeddingGenerator."""

    @pytest.fixture
    def org_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def mock_router_no_embeddings(self):
        """Router with only chat models (no embedding models)."""
        router = MagicMock()
        router.model_list = [
            {"model_name": "groq/llama-3.3-70b-versatile"},
            {"model_name": "openai/gpt-oss-120b"},
        ]
        return router

    @pytest.fixture
    def mock_router_with_embeddings(self):
        """Router with an embedding model available."""
        router = MagicMock()
        router.model_list = [
            {"model_name": "groq/llama-3.3-70b-versatile"},
            {"model_name": "text-embedding-3-small"},
        ]
        return router

    async def test_falls_back_to_platform_key_when_no_org_embeddings(
        self, org_id, mock_router_no_embeddings
    ):
        """When org has no embedding models, should select platform model."""
        gen = EmbeddingGenerator(org_id)
        db = AsyncMock()

        with patch("app.services.gateway.get_router", AsyncMock(return_value=mock_router_no_embeddings)):
            with patch("app.core.config.settings") as mock_settings:
                mock_settings.platform_embedding_api_key = "sk-test-platform-key"
                model = await gen.get_cheapest_embedding_model(db)

        assert model == "text-embedding-3-small"
        assert gen._use_platform_key is True

    async def test_uses_org_model_when_available(
        self, org_id, mock_router_with_embeddings
    ):
        """When org has embedding models, should use them (not platform key)."""
        gen = EmbeddingGenerator(org_id)
        db = AsyncMock()

        with patch("app.services.gateway.get_router", AsyncMock(return_value=mock_router_with_embeddings)):
            model = await gen.get_cheapest_embedding_model(db)

        assert model == "text-embedding-3-small"
        assert gen._use_platform_key is False

    async def test_returns_none_when_no_org_models_and_no_platform_key(
        self, org_id, mock_router_no_embeddings
    ):
        """When org has no embedding models AND no platform key, returns None."""
        gen = EmbeddingGenerator(org_id)
        db = AsyncMock()

        with patch("app.services.gateway.get_router", AsyncMock(return_value=mock_router_no_embeddings)):
            with patch("app.core.config.settings") as mock_settings:
                mock_settings.platform_embedding_api_key = None
                model = await gen.get_cheapest_embedding_model(db)

        assert model is None

    async def test_generate_embeddings_uses_platform_path(self, org_id):
        """generate_embeddings should call _embed_via_platform when flag is set."""
        gen = EmbeddingGenerator(org_id)
        gen._use_platform_key = True

        mock_response = MagicMock()
        mock_response.data = [{"embedding": [0.1, 0.2, 0.3]}]

        with patch("app.services.kb_ingestion.get_db_session") as mock_ctx:
            mock_db = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            # Mock get_cheapest to return platform model
            with patch.object(gen, "get_cheapest_embedding_model", AsyncMock(return_value="text-embedding-3-small")):
                with patch.object(gen, "_embed_via_platform", AsyncMock(return_value=[[0.1, 0.2, 0.3]])) as mock_platform:
                    result = await gen.generate_embeddings(["hello world"])

        mock_platform.assert_called_once_with(["hello world"], None)
        assert result == [[0.1, 0.2, 0.3]]

    async def test_generate_embeddings_uses_router_when_org_has_models(self, org_id):
        """generate_embeddings should use org router when org has embedding models."""
        gen = EmbeddingGenerator(org_id)
        gen._use_platform_key = False

        mock_response = MagicMock()
        mock_response.data = [{"embedding": [0.4, 0.5, 0.6]}]

        mock_router = AsyncMock()
        mock_router.aembedding = AsyncMock(return_value=mock_response)

        with patch("app.services.kb_ingestion.get_db_session") as mock_ctx:
            mock_db = AsyncMock()
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

            with patch.object(gen, "get_cheapest_embedding_model", AsyncMock(return_value="text-embedding-005")):
                with patch("app.services.gateway.get_router", AsyncMock(return_value=mock_router)):
                    result = await gen.generate_embeddings(["hello world"])

        assert result == [[0.4, 0.5, 0.6]]

    async def test_embed_via_platform_calls_litellm_directly(self, org_id):
        """_embed_via_platform should call litellm.aembedding with platform key."""
        gen = EmbeddingGenerator(org_id)

        mock_response = MagicMock()
        mock_response.data = [{"embedding": [0.1] * 768}]

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.platform_embedding_api_key = "sk-test-platform-key"
            with patch("litellm.aembedding", AsyncMock(return_value=mock_response)) as mock_embed:
                result = await gen._embed_via_platform(["test text"])

        mock_embed.assert_called_once()
        call_kwargs = mock_embed.call_args[1]
        assert call_kwargs["api_key"] == "sk-test-platform-key"
        assert call_kwargs["model"] == "text-embedding-3-small"
        assert call_kwargs["dimensions"] == 768
        assert len(result) == 1
        assert len(result[0]) == 768

    async def test_platform_dimensions_default_768(self, org_id):
        """Platform embeddings should default to 768 dims to match pgvector column."""
        gen = EmbeddingGenerator(org_id)
        assert gen.PLATFORM_DIMENSIONS == 768

    async def test_prefers_gcp_over_platform(self, org_id):
        """When org has GCP text-embedding-005, should use that over platform key."""
        gen = EmbeddingGenerator(org_id)
        db = AsyncMock()

        router = MagicMock()
        router.model_list = [
            {"model_name": "text-embedding-005"},
            {"model_name": "groq/llama-3.3-70b-versatile"},
        ]

        with patch("app.services.gateway.get_router", AsyncMock(return_value=router)):
            with patch("app.core.config.settings") as mock_settings:
                mock_settings.platform_embedding_api_key = "sk-test-platform-key"
                model = await gen.get_cheapest_embedding_model(db)

        assert model == "text-embedding-005"
        assert gen._use_platform_key is False
