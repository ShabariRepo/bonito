"""Tests for the model catalog in provider_service."""

import pytest

from app.services.provider_service import (
    AZURE_MODELS,
    GCP_MODELS,
    MOCK_CATALOG,
)


def test_azure_model_count():
    assert len(AZURE_MODELS) == 8


def test_gcp_model_count():
    assert len(GCP_MODELS) == 7


def test_unknown_provider_returns_empty():
    assert MOCK_CATALOG.get("oracle", []) == []


def test_model_metadata_has_required_fields():
    required = {"id", "name", "provider", "provider_model_id", "capabilities", "context_window", "pricing_tier"}
    for provider_type in ("azure", "gcp"):
        for model in MOCK_CATALOG[provider_type]:
            model_dict = model.model_dump()
            for field in required:
                assert field in model_dict, f"Missing {field} in {model.name} ({provider_type})"
                assert model_dict[field] is not None, f"{field} is None in {model.name}"


def test_all_models_have_valid_pricing_tier():
    valid_tiers = {"economy", "standard", "premium"}
    for provider_type in ("azure", "gcp"):
        for model in MOCK_CATALOG[provider_type]:
            assert model.pricing_tier in valid_tiers, f"Invalid tier '{model.pricing_tier}' for {model.name}"


def test_all_models_have_non_empty_name():
    for provider_type in ("azure", "gcp"):
        for model in MOCK_CATALOG[provider_type]:
            assert len(model.name) > 0


def test_azure_models_include_key_models():
    names = {m.name for m in AZURE_MODELS}
    assert "GPT-4o" in names
    assert "GPT-4o Mini" in names
    assert "DALL-E 3" in names


def test_gcp_models_include_key_models():
    names = {m.name for m in GCP_MODELS}
    assert "Gemini 1.5 Pro" in names
    assert "Gemini 1.5 Flash" in names
    assert "Imagen 3" in names


def test_models_have_capabilities_list():
    for provider_type in ("azure", "gcp"):
        for model in MOCK_CATALOG[provider_type]:
            assert isinstance(model.capabilities, list)


def test_models_context_window_non_negative():
    for provider_type in ("azure", "gcp"):
        for model in MOCK_CATALOG[provider_type]:
            assert model.context_window >= 0
