"""Tests for the managed inference service."""

import os
import pytest
from unittest.mock import patch

from app.services.managed_inference import (
    is_managed_provider,
    get_master_key,
    is_managed_available,
    calculate_marked_up_cost,
    get_managed_pricing,
    MANAGED_PROVIDERS,
    MARKUP_RATE,
    MASTER_KEY_ENV,
)


class TestIsManagedProvider:
    def test_groq_is_managed(self):
        assert is_managed_provider("groq") is True

    def test_openai_is_managed(self):
        assert is_managed_provider("openai") is True

    def test_anthropic_is_managed(self):
        assert is_managed_provider("anthropic") is True

    def test_aws_not_managed(self):
        assert is_managed_provider("aws") is False

    def test_azure_not_managed(self):
        assert is_managed_provider("azure") is False

    def test_gcp_not_managed(self):
        assert is_managed_provider("gcp") is False

    def test_unknown_provider_not_managed(self):
        assert is_managed_provider("unknown") is False


class TestGetMasterKey:
    def test_returns_key_when_env_set(self):
        with patch.dict(os.environ, {"BONITO_GROQ_MASTER_KEY": "gsk_test123"}):
            assert get_master_key("groq") == "gsk_test123"

    def test_returns_none_when_env_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            # Clear the specific env var if it exists
            os.environ.pop("BONITO_GROQ_MASTER_KEY", None)
            assert get_master_key("groq") is None

    def test_returns_none_for_unknown_provider(self):
        assert get_master_key("aws") is None

    def test_openai_key_from_env(self):
        with patch.dict(os.environ, {"BONITO_OPENAI_MASTER_KEY": "sk-test456"}):
            assert get_master_key("openai") == "sk-test456"

    def test_anthropic_key_from_env(self):
        with patch.dict(os.environ, {"BONITO_ANTHROPIC_MASTER_KEY": "sk-ant-test789"}):
            assert get_master_key("anthropic") == "sk-ant-test789"


class TestIsManagedAvailable:
    def test_available_when_key_configured(self):
        with patch.dict(os.environ, {"BONITO_GROQ_MASTER_KEY": "gsk_test"}):
            assert is_managed_available("groq") is True

    def test_not_available_when_key_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("BONITO_GROQ_MASTER_KEY", None)
            assert is_managed_available("groq") is False

    def test_not_available_for_non_managed_provider(self):
        assert is_managed_available("aws") is False

    def test_all_providers_with_keys(self):
        env = {v: "test_key_value" for v in MASTER_KEY_ENV.values()}
        with patch.dict(os.environ, env):
            for pt in MANAGED_PROVIDERS:
                assert is_managed_available(pt) is True


class TestCalculateMarkedUpCost:
    def test_basic_markup(self):
        result = calculate_marked_up_cost(1.0)
        assert result == pytest.approx(1.33, rel=1e-2)

    def test_zero_cost(self):
        assert calculate_marked_up_cost(0.0) == 0.0

    def test_small_cost(self):
        result = calculate_marked_up_cost(0.001)
        expected = 0.001 * (1 + MARKUP_RATE)
        assert result == pytest.approx(expected, rel=1e-4)

    def test_large_cost(self):
        result = calculate_marked_up_cost(100.0)
        assert result == pytest.approx(133.0, rel=1e-2)


class TestGetManagedPricing:
    def test_groq_pricing(self):
        pricing = get_managed_pricing("groq")
        assert "input_per_1k" in pricing
        assert "output_per_1k" in pricing
        assert "markup_rate" in pricing
        assert pricing["markup_rate"] == MARKUP_RATE
        # Verify markup applied
        assert pricing["input_per_1k"] > pricing["base_input_per_1k"]
        assert pricing["output_per_1k"] > pricing["base_output_per_1k"]

    def test_openai_pricing(self):
        pricing = get_managed_pricing("openai")
        assert pricing["markup_rate"] == MARKUP_RATE
        assert pricing["input_per_1k"] == pytest.approx(
            pricing["base_input_per_1k"] * (1 + MARKUP_RATE), rel=1e-4
        )

    def test_anthropic_pricing(self):
        pricing = get_managed_pricing("anthropic")
        assert len(pricing) > 0
        assert pricing["markup_rate"] == MARKUP_RATE

    def test_unknown_provider_returns_empty(self):
        assert get_managed_pricing("aws") == {}
        assert get_managed_pricing("unknown") == {}


class TestCredentialValidation:
    """Test that validate_credentials handles managed=true correctly."""

    def test_managed_true_skips_validation(self):
        from app.services.provider_service import validate_credentials

        with patch.dict(os.environ, {"BONITO_GROQ_MASTER_KEY": "gsk_test"}):
            valid, error = validate_credentials("groq", {"managed": True})
            assert valid is True
            assert error == ""

    def test_managed_true_fails_when_key_not_configured(self):
        from app.services.provider_service import validate_credentials

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("BONITO_GROQ_MASTER_KEY", None)
            valid, error = validate_credentials("groq", {"managed": True})
            assert valid is False
            assert "not available" in error.lower()

    def test_managed_true_fails_for_non_managed_provider(self):
        from app.services.provider_service import validate_credentials

        valid, error = validate_credentials("aws", {"managed": True})
        assert valid is False

    def test_normal_credentials_still_validated(self):
        from app.services.provider_service import validate_credentials

        valid, error = validate_credentials("groq", {"api_key": "gsk_" + "x" * 50})
        assert valid is True


class TestManagedAvailabilityEndpoint:
    """Test the managed-availability API endpoint structure."""

    def test_managed_providers_set(self):
        """Verify the managed providers constant includes expected providers."""
        assert "groq" in MANAGED_PROVIDERS
        assert "openai" in MANAGED_PROVIDERS
        assert "anthropic" in MANAGED_PROVIDERS
        assert "aws" not in MANAGED_PROVIDERS
        assert "azure" not in MANAGED_PROVIDERS
        assert "gcp" not in MANAGED_PROVIDERS

    def test_master_key_env_vars_defined(self):
        """Verify env var names are defined for all managed providers."""
        for pt in MANAGED_PROVIDERS:
            assert pt in MASTER_KEY_ENV
            assert MASTER_KEY_ENV[pt].startswith("BONITO_")
