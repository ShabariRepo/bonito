"""Pytest fixtures for Bonito backend tests."""

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.redis import get_redis
from app.main import app as fastapi_app
from app.services import auth_service
from app.models.user import User
from app.models.organization import Organization

# Import all models so Base.metadata.create_all creates all tables
import app.models  # noqa: F401

# Mark the test environment so middleware (e.g. rate limiter) can skip
os.environ["TESTING"] = "1"

# Ensure required secrets are available for tests (vault isn't running locally)
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-unit-tests")

# Patch the already-instantiated settings object so auth_service picks up the key
from app.core.config import settings as _settings
if not _settings.secret_key:
    _settings.secret_key = "test-secret-key-for-unit-tests"

# Use DATABASE_URL from environment if available (CI sets PostgreSQL),
# otherwise fall back to in-memory SQLite for local dev.
TEST_DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///:memory:")


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
async def mock_redis():
    """Create a mock Redis that supports basic operations."""
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.incr = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    return mock


@pytest_asyncio.fixture(scope="function")
async def client(test_engine, mock_redis) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_redis] = lambda: mock_redis

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()


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

    fastapi_app.dependency_overrides[get_db] = override_get_db
    fastapi_app.dependency_overrides[get_redis] = lambda: mock_redis

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()


# ── Cloud Provider / Vault mocks (auto-use) ─────────────────────

class _FakeCredentialInfo:
    valid = True
    account_id = "123456789012"
    arn = "arn:aws:iam::123456789012:user/test"
    user_id = "AIDAEXAMPLE"
    message = "Credentials valid (test)"


@pytest.fixture(autouse=True)
def mock_cloud_providers():
    """Prevent tests from calling real cloud APIs (AWS STS, Azure, GCP)."""
    fake = AsyncMock(return_value=_FakeCredentialInfo())
    with (
        patch("app.services.providers.aws_bedrock.AWSBedrockProvider.validate_credentials", fake),
        patch("app.services.providers.azure_foundry.AzureFoundryProvider.validate_credentials", fake),
        patch("app.services.providers.gcp_vertex.GCPVertexProvider.validate_credentials", fake),
        patch("app.services.provider_service.store_credentials_in_vault", AsyncMock(return_value="vault:test")),
    ):
        yield


# ── Auth helpers ─────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def test_org(test_engine) -> Organization:
    """Create a test organization and return it."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        org = Organization(name="Test Organization")
        session.add(org)
        await session.commit()
        await session.refresh(org)
        return org


@pytest_asyncio.fixture(scope="function")
async def test_org_b(test_engine) -> Organization:
    """Create a second test organization for multi-tenancy tests."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        org = Organization(name="Other Organization")
        session.add(org)
        await session.commit()
        await session.refresh(org)
        return org


@pytest_asyncio.fixture(scope="function")
async def test_user(test_engine, test_org) -> User:
    """Create a verified test user with known credentials."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        user = User(
            email="test@bonito.ai",
            hashed_password=auth_service.hash_password("TestPass123"),
            name="Test User",
            org_id=test_org.id,
            role="admin",
            email_verified=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture(scope="function")
async def test_user_b(test_engine, test_org_b) -> User:
    """Create a verified test user in org B."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        user = User(
            email="other@bonito.ai",
            hashed_password=auth_service.hash_password("TestPass123"),
            name="Other User",
            org_id=test_org_b.id,
            role="admin",
            email_verified=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture(scope="function")
async def auth_token(test_user, test_org) -> str:
    """Get a valid JWT access token for the test user."""
    return auth_service.create_access_token(
        str(test_user.id), str(test_org.id), test_user.role
    )


@pytest_asyncio.fixture(scope="function")
async def auth_token_b(test_user_b, test_org_b) -> str:
    """Get a valid JWT access token for the test user in org B."""
    return auth_service.create_access_token(
        str(test_user_b.id), str(test_org_b.id), test_user_b.role
    )


@pytest_asyncio.fixture(scope="function")
async def auth_headers(auth_token) -> dict:
    """Return authorization headers for the test user."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture(scope="function")
async def auth_headers_b(auth_token_b) -> dict:
    """Return authorization headers for org B's test user."""
    return {"Authorization": f"Bearer {auth_token_b}"}


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
