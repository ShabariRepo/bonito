"""Tests for the /api/analytics endpoints — verify real DB queries, no hardcoded data."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analytics_overview_structure(client: AsyncClient, auth_headers):
    resp = await client.get("/api/analytics/overview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    # Must have all expected keys from the real analytics service
    expected_keys = {
        "total_requests",
        "total_cost",
        "active_models",
        "active_teams",
        "top_model",
        "avg_latency_ms",
        "success_rate",
        "active_users",
    }
    assert expected_keys.issubset(data.keys()), f"Missing keys: {expected_keys - data.keys()}"


@pytest.mark.asyncio
async def test_analytics_overview_empty_returns_zeros(client: AsyncClient, auth_headers):
    """With no gateway data, overview should return zeros, not fake numbers."""
    resp = await client.get("/api/analytics/overview", headers=auth_headers)
    data = resp.json()
    assert data["total_requests"] == 0
    assert data["total_cost"] == 0
    assert data["active_models"] == 0
    assert data["active_teams"] == 0
    assert data["top_model"] is None
    assert data["avg_latency_ms"] == 0
    assert data["success_rate"] == 0.0
    assert data["active_users"] == 0


@pytest.mark.asyncio
async def test_analytics_usage_structure(client: AsyncClient, auth_headers):
    resp = await client.get("/api/analytics/usage?period=day", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"] == "day"
    assert "data" in data
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_analytics_usage_week_period(client: AsyncClient, auth_headers):
    resp = await client.get("/api/analytics/usage?period=week", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["period"] == "week"


@pytest.mark.asyncio
async def test_analytics_usage_month_period(client: AsyncClient, auth_headers):
    resp = await client.get("/api/analytics/usage?period=month", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["period"] == "month"


@pytest.mark.asyncio
async def test_analytics_usage_empty_returns_empty_list(client: AsyncClient, auth_headers):
    resp = await client.get("/api/analytics/usage?period=day", headers=auth_headers)
    data = resp.json()
    assert data["data"] == []


@pytest.mark.asyncio
async def test_analytics_costs_structure(client: AsyncClient, auth_headers):
    resp = await client.get("/api/analytics/costs", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "by_provider" in data
    assert "by_model" in data
    assert "by_team" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_analytics_costs_empty_returns_zeros(client: AsyncClient, auth_headers):
    resp = await client.get("/api/analytics/costs", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 0
    assert data["by_provider"] == []
    assert data["by_model"] == []
    assert data["by_team"] == []


@pytest.mark.asyncio
async def test_analytics_trends_structure(client: AsyncClient, auth_headers):
    resp = await client.get("/api/analytics/trends", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "cost_trend" in data
    assert "request_trend" in data
    assert "efficiency_trend" in data
    assert "model_shifts" in data

    # Check nested structure
    for trend_key in ("cost_trend", "request_trend"):
        trend = data[trend_key]
        assert "direction" in trend
        assert "percentage" in trend


@pytest.mark.asyncio
async def test_analytics_digest_structure(client: AsyncClient, auth_headers):
    resp = await client.get("/api/analytics/digest", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "period" in data
    assert "summary" in data
    summary = data["summary"]
    assert "total_requests" in summary
    assert "total_cost" in summary


@pytest.mark.asyncio
async def test_analytics_digest_empty_returns_zeros(client: AsyncClient, auth_headers):
    resp = await client.get("/api/analytics/digest", headers=auth_headers)
    data = resp.json()
    assert data["summary"]["total_requests"] == 0
    assert data["summary"]["total_cost"] == 0


@pytest.mark.asyncio
async def test_analytics_requires_auth(client: AsyncClient):
    resp = await client.get("/api/analytics/overview")
    assert resp.status_code == 403
