"""Tests for the /api/health endpoint."""

import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200_with_healthy_status(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_shows_redis_connected(client: AsyncClient):
    resp = await client.get("/api/health")
    data = resp.json()
    assert data["redis"] == "connected"


@pytest.mark.asyncio
async def test_health_shows_redis_disconnected_on_failure(client_no_redis: AsyncClient):
    resp = await client_no_redis.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["redis"] == "disconnected"
