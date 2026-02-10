"""Tests for the /api/auth endpoints."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.services import auth_service


@pytest.mark.asyncio
async def test_register_with_valid_password(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "email": "newuser@bonito.ai",
        "password": "StrongPass1",
        "name": "New User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "message" in data
    assert "Registration successful" in data["message"]


@pytest.mark.asyncio
async def test_register_with_weak_password_no_uppercase(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "email": "weak@bonito.ai",
        "password": "weakpass1",
        "name": "Weak User",
    })
    assert resp.status_code == 422
    assert "uppercase" in resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_register_with_weak_password_no_digit(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "email": "weak2@bonito.ai",
        "password": "WeakPassNoDigit",
        "name": "Weak User",
    })
    assert resp.status_code == 422
    assert "number" in resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_register_with_short_password(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "email": "short@bonito.ai",
        "password": "Ab1",
        "name": "Short Pass",
    })
    assert resp.status_code == 422
    assert "8 characters" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_register_with_weak_password_no_lowercase(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "email": "weak3@bonito.ai",
        "password": "ALLUPPERCASE1",
        "name": "No Lower",
    })
    assert resp.status_code == 422
    assert "lowercase" in resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "email": "dupe@bonito.ai",
        "password": "StrongPass1",
        "name": "First User",
    })
    resp = await client.post("/api/auth/register", json={
        "email": "dupe@bonito.ai",
        "password": "StrongPass1",
        "name": "Second User",
    })
    assert resp.status_code == 409
    assert "already registered" in resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user, mock_redis):
    # mock_redis.set is already mocked, and store_session calls redis.set
    mock_redis.get = AsyncMock(return_value=None)

    resp = await client.post("/api/auth/login", json={
        "email": "test@bonito.ai",
        "password": "TestPass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    resp = await client.post("/api/auth/login", json={
        "email": "test@bonito.ai",
        "password": "WrongPass123",
    })
    assert resp.status_code == 401
    assert "Invalid credentials" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_login_nonexistent_email(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={
        "email": "nobody@bonito.ai",
        "password": "Whatever123",
    })
    assert resp.status_code == 401
    assert "Invalid credentials" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_login_unverified_email(client: AsyncClient, test_engine):
    """Unverified users should not be able to log in."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from app.models.user import User
    from app.models.organization import Organization

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        org = Organization(name="Unverified Org")
        session.add(org)
        await session.commit()
        await session.refresh(org)

        user = User(
            email="unverified@bonito.ai",
            hashed_password=auth_service.hash_password("TestPass123"),
            name="Unverified",
            org_id=org.id,
            role="admin",
            email_verified=False,
        )
        session.add(user)
        await session.commit()

    resp = await client.post("/api/auth/login", json={
        "email": "unverified@bonito.ai",
        "password": "TestPass123",
    })
    assert resp.status_code == 403
    assert "verify your email" in resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_token_refresh(client: AsyncClient, test_user, mock_redis):
    """Test the token refresh flow."""
    # Login first to get tokens
    mock_redis.get = AsyncMock(return_value=None)
    login_resp = await client.post("/api/auth/login", json={
        "email": "test@bonito.ai",
        "password": "TestPass123",
    })
    assert login_resp.status_code == 200
    refresh_token = login_resp.json()["refresh_token"]

    # Now mock redis to say the session is valid
    mock_redis.get = AsyncMock(return_value=refresh_token)

    refresh_resp = await client.post("/api/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_token_refresh_with_invalid_token(client: AsyncClient):
    resp = await client.post("/api/auth/refresh", json={
        "refresh_token": "invalid.token.here",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint(client: AsyncClient, test_user, auth_headers):
    resp = await client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@bonito.ai"
    assert data["name"] == "Test User"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_me_without_auth(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 403  # HTTPBearer returns 403 when no token


@pytest.mark.asyncio
async def test_forgot_password_returns_success_regardless(client: AsyncClient, test_user):
    """Forgot password should always return success to prevent email enumeration."""
    # With existing email
    resp = await client.post("/api/auth/forgot-password", json={
        "email": "test@bonito.ai",
    })
    assert resp.status_code == 200
    assert "message" in resp.json()

    # With non-existing email
    resp2 = await client.post("/api/auth/forgot-password", json={
        "email": "nonexistent@bonito.ai",
    })
    assert resp2.status_code == 200
    assert resp2.json()["message"] == resp.json()["message"]


@pytest.mark.asyncio
async def test_reset_password_with_expired_token(client: AsyncClient, test_engine, test_user):
    """Reset should fail if token is expired."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from app.models.user import User

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.email == "test@bonito.ai"))
        user = result.scalar_one()
        user.reset_token = "expired-test-token"
        user.reset_token_expires_at = datetime.now(timezone.utc) - timedelta(hours=2)
        await session.commit()

    resp = await client.post("/api/auth/reset-password", json={
        "token": "expired-test-token",
        "password": "NewStrongPass1",
    })
    assert resp.status_code == 400
    assert "expired" in resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_reset_password_with_invalid_token(client: AsyncClient):
    resp = await client.post("/api/auth/reset-password", json={
        "token": "totally-fake-token",
        "password": "NewStrongPass1",
    })
    assert resp.status_code == 400
    assert "invalid" in resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_reset_password_success(client: AsyncClient, test_engine, test_user):
    """Reset should succeed with a valid, unexpired token."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from app.models.user import User

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(select(User).where(User.email == "test@bonito.ai"))
        user = result.scalar_one()
        user.reset_token = "valid-test-token"
        user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await session.commit()

    resp = await client.post("/api/auth/reset-password", json={
        "token": "valid-test-token",
        "password": "NewStrongPass1",
    })
    assert resp.status_code == 200
    assert "reset successfully" in resp.json()["message"].lower()
