"""Tests for model details and playground functionality."""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.model import Model
from app.models.cloud_provider import CloudProvider
from app.models.gateway import GatewayRequest
from app.models.policy import Policy


async def _create_provider_and_model(test_engine, org_id, model_id="claude-3-sonnet", display_name="Claude 3 Sonnet", pricing_info=None):
    """Helper to create a provider + model in the test DB."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        provider = CloudProvider(org_id=org_id, provider_type="aws", status="active")
        session.add(provider)
        await session.flush()
        await session.refresh(provider)

        model = Model(
            provider_id=provider.id,
            model_id=model_id,
            display_name=display_name,
            capabilities={"types": ["chat", "code"]},
            pricing_info=pricing_info or {
                "context_window": 200000,
                "input_price_per_1k": 0.003,
                "output_price_per_1k": 0.015,
                "status": "available"
            },
        )
        session.add(model)
        await session.commit()
        await session.refresh(model)
        return provider, model


@pytest.mark.asyncio
async def test_model_details_returns_enriched_data(client, auth_headers, test_org, test_user, test_engine):
    """Test that model details endpoint returns enriched model information."""
    provider, model = await _create_provider_and_model(test_engine, test_org.id)

    # Add some gateway request logs
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        for cost in (0.45, 0.675):
            req = GatewayRequest(
                org_id=test_org.id,
                user_id=test_user.id,
                model_requested="claude-3-sonnet",
                input_tokens=100,
                output_tokens=200,
                cost=cost,
                status="success",
            )
            session.add(req)
        await session.commit()

    response = await client.get(f"/api/models/{model.id}/details", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["display_name"] == "Claude 3 Sonnet"
    assert data["model_id"] == "claude-3-sonnet"
    assert data["provider_type"] == "aws"
    assert data["context_window"] == 200000
    assert data["input_price_per_1k"] == 0.003
    assert data["output_price_per_1k"] == 0.015


@pytest.mark.asyncio
async def test_model_details_not_found(client, auth_headers):
    """Test that model details endpoint returns 404 for non-existent model."""
    fake_id = uuid4()
    response = await client.get(f"/api/models/{fake_id}/details", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_model_details_cross_org_blocked(client, auth_headers_b, test_org, test_engine):
    """Test that users can't access models from other organizations."""
    provider, model = await _create_provider_and_model(test_engine, test_org.id)

    # Org B user tries to access org A's model
    response = await client.get(f"/api/models/{model.id}/details", headers=auth_headers_b)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_playground_requires_auth(client):
    """Test that playground endpoints require authentication."""
    fake_id = uuid4()
    response = await client.post(f"/api/models/{fake_id}/playground", json={
        "messages": [{"role": "user", "content": "test"}]
    })
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_compare_max_4_models_enforced(client, auth_headers, test_org, test_engine):
    """Test that model comparison is limited to 4 models maximum."""
    models = []
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        provider = CloudProvider(org_id=test_org.id, provider_type="aws", status="active")
        session.add(provider)
        await session.flush()
        await session.refresh(provider)

        for i in range(5):
            m = Model(
                provider_id=provider.id,
                model_id=f"model-{i}",
                display_name=f"Model {i}",
                capabilities={"types": ["chat"]},
                pricing_info={},
            )
            session.add(m)
            models.append(m)
        await session.commit()
        for m in models:
            await session.refresh(m)

    request_data = {
        "model_ids": [str(m.id) for m in models],
        "messages": [{"role": "user", "content": "test"}],
        "temperature": 0.7,
    }

    response = await client.post("/api/models/compare", headers=auth_headers, json=request_data)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_compare_cross_org_blocked(client, auth_headers, test_org, test_org_b, test_engine):
    """Test that model comparison blocks cross-org access."""
    _, model_a = await _create_provider_and_model(test_engine, test_org.id, "model-a", "Model A")
    _, model_b = await _create_provider_and_model(test_engine, test_org_b.id, "model-b", "Model B")

    request_data = {
        "model_ids": [str(model_a.id), str(model_b.id)],
        "messages": [{"role": "user", "content": "test"}],
    }

    response = await client.post("/api/models/compare", headers=auth_headers, json=request_data)
    # Should 404 because model_b isn't visible to org A
    assert response.status_code == 404


@pytest.mark.asyncio
@patch("app.services.provider_service._get_provider_secrets", new_callable=AsyncMock, return_value={"access_key_id": "AKIAIOSFODNN7EXAMPLE", "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "region": "us-east-1"})
@patch("litellm.acompletion", new_callable=AsyncMock)
async def test_playground_execute_basic(mock_acompletion, mock_secrets, client, auth_headers, test_org, test_user, test_engine):
    """Test basic playground execution with mocked LiteLLM call."""
    mock_msg = type("Msg", (), {"content": "Hello! I'm here to help.", "role": "assistant"})()
    mock_choice = type("Choice", (), {"message": mock_msg, "index": 0, "finish_reason": "stop"})()
    mock_usage = type("Usage", (), {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25})()
    mock_resp = type("Resp", (), {"choices": [mock_choice], "usage": mock_usage, "model": "claude-3-sonnet"})()
    mock_acompletion.return_value = mock_resp

    _, model = await _create_provider_and_model(test_engine, test_org.id)

    response = await client.post(
        f"/api/models/{model.id}/playground",
        headers=auth_headers,
        json={
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 0.7,
            "max_tokens": 100,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Hello! I'm here to help."
    assert data["usage"]["total_tokens"] == 25
    assert data["cost"] > 0
    assert data["latency_ms"] >= 0


@pytest.mark.asyncio
@patch("app.services.provider_service._get_provider_secrets", new_callable=AsyncMock, return_value={"access_key_id": "AKIAIOSFODNN7EXAMPLE", "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "region": "us-east-1"})
@patch("litellm.acompletion", new_callable=AsyncMock)
async def test_compare_multiple_models(mock_acompletion, mock_secrets, client, auth_headers, test_org, test_engine):
    """Test multi-model comparison endpoint."""
    responses = []
    for i, name in enumerate(["Sonnet", "Haiku"]):
        msg = type("Msg", (), {"content": f"Response from {name}", "role": "assistant"})()
        choice = type("Choice", (), {"message": msg, "index": 0, "finish_reason": "stop"})()
        usage = type("Usage", (), {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25})()
        responses.append(type("Resp", (), {"choices": [choice], "usage": usage, "model": f"model-{i}"})())

    mock_acompletion.side_effect = responses

    _, model1 = await _create_provider_and_model(test_engine, test_org.id, "model-0", "Sonnet")
    _, model2 = await _create_provider_and_model(test_engine, test_org.id, "model-1", "Haiku",
                                                  pricing_info={"input_price_per_1k": 0.001, "output_price_per_1k": 0.005})

    response = await client.post(
        "/api/models/compare",
        headers=auth_headers,
        json={
            "model_ids": [str(model1.id), str(model2.id)],
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 0.7,
            "max_tokens": 100,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2
    assert data["results"][0]["response"] == "Response from Sonnet"
    assert data["results"][1]["response"] == "Response from Haiku"
