"""Pytest fixtures for Bonito backend tests."""

import asyncio
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.redis import get_redis
from app.main import app

# Import all models so Base.metadata.create_all creates all tables
import app.models  # noqa: F401

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = lambda: mock_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def client_no_redis(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """Client where Redis ping fails."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(side_effect=ConnectionError("Redis down"))

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = lambda: mock_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Test Data Helpers ──────────────────────────────────────────────

AWS_CREDENTIALS = {
    "access_key_id": "AKIAIOSFODNN7EXAMPLE",
    "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "region": "us-east-1",
}

AZURE_CREDENTIALS = {
    "tenant_id": "12345678-1234-1234-1234-123456789012",
    "client_id": "12345678-1234-1234-1234-123456789013",
    "client_secret": "super-secret-value-here",
    "subscription_id": "12345678-1234-1234-1234-123456789014",
}

GCP_CREDENTIALS = {
    "project_id": "my-bonito-project",
    "service_account_json": '{"type":"service_account","project_id":"my-bonito-project"}',
}


async def create_provider(client: AsyncClient, provider_type: str = "aws", credentials: dict | None = None) -> dict:
    """Helper to create a provider and return the response JSON."""
    cred_map = {"aws": AWS_CREDENTIALS, "azure": AZURE_CREDENTIALS, "gcp": GCP_CREDENTIALS}
    creds = credentials or cred_map[provider_type]
    resp = await client.post("/api/providers/connect", json={"provider_type": provider_type, "credentials": creds})
    assert resp.status_code == 201
    return resp.json()
