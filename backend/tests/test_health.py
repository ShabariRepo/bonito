"""Tests for the /api/health endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_basic_returns_200(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "alive"
    assert data["service"] == "bonito-api"


@pytest.mark.asyncio
async def test_health_liveness(client: AsyncClient):
    resp = await client.get("/api/health/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_readiness(client: AsyncClient):
    resp = await client.get("/api/health/ready")
    assert resp.status_code in (200, 503)
    # Even if vault/redis are mocked, we should get a structured response
    data = resp.json()
    if resp.status_code == 200:
        assert data["status"] in ("healthy", "degraded")
        assert "dependencies" in data
