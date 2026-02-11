"""Tests for routing policies endpoints."""

import pytest
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.routing_policy import RoutingPolicy
from app.models.model import Model
from app.models.cloud_provider import CloudProvider


async def _create_provider_and_models(test_engine, org_id, count=1):
    """Helper to create provider + N models in the test DB."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        provider = CloudProvider(org_id=org_id, provider_type="aws", status="active")
        session.add(provider)
        await session.flush()
        await session.refresh(provider)

        models = []
        for i in range(count):
            m = Model(
                provider_id=provider.id,
                model_id=f"model-{i}",
                display_name=f"Model {i}",
                capabilities={"types": ["text"]},
                pricing_info={"input_price_per_1k": 0.003},
            )
            session.add(m)
            models.append(m)
        await session.commit()
        for m in models:
            await session.refresh(m)
        return provider, models


async def _create_policy(test_engine, org_id, name="Test Policy", strategy="balanced", models_json=None, prefix=None):
    """Helper to create a routing policy directly in DB."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        policy = RoutingPolicy(
            org_id=org_id,
            name=name,
            strategy=strategy,
            models=models_json or [],
            rules={},
            api_key_prefix=prefix or f"rt-{uuid4().hex[:12]}",
        )
        session.add(policy)
        await session.commit()
        await session.refresh(policy)
        return policy


@pytest.mark.asyncio
async def test_create_routing_policy(client, auth_headers, test_org, test_engine):
    """Test creating a valid routing policy."""
    _, models = await _create_provider_and_models(test_engine, test_org.id)

    response = await client.post("/api/routing-policies/", headers=auth_headers, json={
        "name": "Prod Chat",
        "description": "Production chat route",
        "strategy": "cost_optimized",
        "models": [{"model_id": str(models[0].id), "weight": 100, "role": "primary"}],
        "rules": {"max_cost_per_request": 0.05, "max_tokens": 4000},
        "is_active": True,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Prod Chat"
    assert data["strategy"] == "cost_optimized"
    assert data["api_key_prefix"].startswith("rt-")


@pytest.mark.asyncio
async def test_list_routing_policies_scoped_to_org(client, auth_headers, auth_headers_b, test_org, test_org_b, test_engine):
    """Org A only sees its own policies."""
    await _create_policy(test_engine, test_org.id, "Policy A", prefix="rt-a1234567")
    await _create_policy(test_engine, test_org_b.id, "Policy B", prefix="rt-b1234567")

    resp_a = await client.get("/api/routing-policies/", headers=auth_headers)
    assert resp_a.status_code == 200
    names_a = [p["name"] for p in resp_a.json()]
    assert "Policy A" in names_a
    assert "Policy B" not in names_a

    resp_b = await client.get("/api/routing-policies/", headers=auth_headers_b)
    names_b = [p["name"] for p in resp_b.json()]
    assert "Policy B" in names_b
    assert "Policy A" not in names_b


@pytest.mark.asyncio
async def test_get_routing_policy_detail(client, auth_headers, test_org, test_engine):
    """Test retrieving policy details with resolved model names."""
    _, models = await _create_provider_and_models(test_engine, test_org.id)
    policy = await _create_policy(
        test_engine, test_org.id, "Detail Test",
        strategy="latency_optimized",
        models_json=[{"model_id": str(models[0].id), "weight": 100, "role": "primary"}],
    )

    response = await client.get(f"/api/routing-policies/{policy.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Detail Test"
    assert "model_names" in data
    assert str(models[0].id) in data["model_names"]


@pytest.mark.asyncio
async def test_update_routing_policy(client, auth_headers, test_org, test_engine):
    """Test updating a routing policy."""
    policy = await _create_policy(test_engine, test_org.id, "Original")

    response = await client.put(f"/api/routing-policies/{policy.id}", headers=auth_headers, json={
        "name": "Updated",
        "strategy": "cost_optimized",
        "is_active": False,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    assert data["strategy"] == "cost_optimized"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_delete_routing_policy(client, auth_headers, test_org, test_engine):
    """Test deleting a routing policy."""
    policy = await _create_policy(test_engine, test_org.id, "To Delete")

    response = await client.delete(f"/api/routing-policies/{policy.id}", headers=auth_headers)
    assert response.status_code == 204

    get_resp = await client.get(f"/api/routing-policies/{policy.id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_create_policy_invalid_model_ids(client, auth_headers, test_org_b, test_engine):
    """Models from wrong org should be rejected."""
    _, models_b = await _create_provider_and_models(test_engine, test_org_b.id)

    response = await client.post("/api/routing-policies/", headers=auth_headers, json={
        "name": "Invalid",
        "strategy": "balanced",
        "models": [{"model_id": str(models_b[0].id), "weight": 100, "role": "primary"}],
        "rules": {},
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_policy_cross_org_isolation(client, auth_headers, test_org_b, test_engine):
    """Org A cannot access org B's policies."""
    policy_b = await _create_policy(test_engine, test_org_b.id, "Org B Policy")

    assert (await client.get(f"/api/routing-policies/{policy_b.id}", headers=auth_headers)).status_code == 404
    assert (await client.put(f"/api/routing-policies/{policy_b.id}", headers=auth_headers, json={"name": "Hacked"})).status_code == 404
    assert (await client.delete(f"/api/routing-policies/{policy_b.id}", headers=auth_headers)).status_code == 404


@pytest.mark.asyncio
async def test_test_policy_returns_model_selection(client, auth_headers, test_org, test_engine):
    """Policy test endpoint returns which model would be selected."""
    _, models = await _create_provider_and_models(test_engine, test_org.id)
    policy = await _create_policy(
        test_engine, test_org.id, "Test Route",
        strategy="cost_optimized",
        models_json=[{"model_id": str(models[0].id), "weight": 100, "role": "primary"}],
    )

    response = await client.post(f"/api/routing-policies/{policy.id}/test", headers=auth_headers, json={
        "prompt": "Summarize this document",
        "max_tokens": 1000,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["selected_model_id"] == str(models[0].id)
    assert data["strategy_used"] == "cost_optimized"
    assert "selection_reason" in data


@pytest.mark.asyncio
async def test_policy_requires_auth(client):
    """Routing policy endpoints require auth."""
    assert (await client.get("/api/routing-policies/")).status_code in (401, 403)
    assert (await client.post("/api/routing-policies/", json={"name": "test"})).status_code in (401, 403)
    fake = str(uuid4())
    assert (await client.get(f"/api/routing-policies/{fake}")).status_code in (401, 403)


@pytest.mark.asyncio
async def test_ab_test_weights_must_sum_to_100(client, auth_headers, test_org, test_engine):
    """A/B test weights validation."""
    _, models = await _create_provider_and_models(test_engine, test_org.id, count=2)

    # Weights sum to 90 — should fail
    response = await client.post("/api/routing-policies/", headers=auth_headers, json={
        "name": "A/B Test",
        "strategy": "ab_test",
        "models": [
            {"model_id": str(models[0].id), "weight": 40, "role": "primary"},
            {"model_id": str(models[1].id), "weight": 50, "role": "fallback"},
        ],
        "rules": {},
    })
    assert response.status_code == 422

    # Weights sum to 100 — should pass
    response = await client.post("/api/routing-policies/", headers=auth_headers, json={
        "name": "A/B Test",
        "strategy": "ab_test",
        "models": [
            {"model_id": str(models[0].id), "weight": 60, "role": "primary"},
            {"model_id": str(models[1].id), "weight": 40, "role": "fallback"},
        ],
        "rules": {},
    })
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_failover_requires_at_least_2_models(client, auth_headers, test_org, test_engine):
    """Failover strategy needs ≥2 models."""
    _, models = await _create_provider_and_models(test_engine, test_org.id, count=2)

    # 1 model — should fail
    response = await client.post("/api/routing-policies/", headers=auth_headers, json={
        "name": "Failover",
        "strategy": "failover",
        "models": [{"model_id": str(models[0].id), "role": "primary"}],
        "rules": {},
    })
    assert response.status_code == 422

    # 2 models — should pass
    response = await client.post("/api/routing-policies/", headers=auth_headers, json={
        "name": "Failover",
        "strategy": "failover",
        "models": [
            {"model_id": str(models[0].id), "role": "primary"},
            {"model_id": str(models[1].id), "role": "fallback"},
        ],
        "rules": {},
    })
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_get_policy_stats(client, auth_headers, test_org, test_engine):
    """Policy stats endpoint returns usage data."""
    policy = await _create_policy(test_engine, test_org.id, "Stats Policy")

    response = await client.get(f"/api/routing-policies/{policy.id}/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["policy_id"] == str(policy.id)
    assert "request_count" in data
    assert "total_cost" in data
