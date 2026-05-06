"""
Regression tests for specific bug fixes.

Each test is marked with @pytest.mark.regression so they can be run
independently via: pytest -m regression
"""

import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.redis import get_redis
from app.main import app as asgi_app, fastapi_app
from app.models.organization import Organization
from app.models.user import User
from app.services import auth_service

# Import all models so tables are created
import app.models  # noqa: F401


# ---------------------------------------------------------------------------
# 1. Redis deferred import — FeatureGateService and UsageTracker
# ---------------------------------------------------------------------------

@pytest.mark.regression
def test_feature_gate_redis_deferred_import():
    """
    Bug: FeatureGateService captured `redis_client` at import time (None).
    Fix: @property does a deferred import so it always reads the current value.
    """
    mock_redis = MagicMock(name="mock_redis_client")

    with patch("app.core.redis.redis_client", mock_redis):
        from app.services.feature_gate import FeatureGateService

        svc = FeatureGateService()
        assert svc.redis is mock_redis, (
            "FeatureGateService.redis should read the current redis_client, not a stale None"
        )


@pytest.mark.regression
def test_usage_tracker_redis_deferred_import():
    """
    Bug: UsageTracker captured `redis_client` at import time (None).
    Fix: @property does a deferred import so it always reads the current value.
    """
    mock_redis = MagicMock(name="mock_redis_client")

    with patch("app.core.redis.redis_client", mock_redis):
        from app.services.usage_tracker import UsageTracker

        tracker = UsageTracker()
        assert tracker.redis is mock_redis, (
            "UsageTracker.redis should read the current redis_client, not a stale None"
        )


# ---------------------------------------------------------------------------
# Helpers — superadmin-capable client
# ---------------------------------------------------------------------------

# The test user's email from conftest is "test@bonito.ai".  We set
# ADMIN_EMAILS so that `require_superadmin` accepts it.
os.environ.setdefault("ADMIN_EMAILS", "test@bonito.ai")

# Patch settings object directly in case it was already loaded
from app.core.config import settings as _settings
if not _settings.admin_emails:
    _settings.admin_emails = "test@bonito.ai"


# ---------------------------------------------------------------------------
# 2. Admin tier change syncs bonobot fields (POST endpoint)
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.asyncio
async def test_admin_tier_enterprise_syncs_bonobot(client, test_org, auth_headers):
    """
    Setting tier to 'enterprise' via POST /api/admin/organizations/{id}/tier
    should auto-sync bonobot_plan='enterprise' and bonobot_agent_limit=-1.
    """
    resp = await client.post(
        f"/api/admin/organizations/{test_org.id}/tier",
        json={"tier": "enterprise"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["subscription_tier"] == "enterprise"
    assert data["bonobot_plan"] == "enterprise"
    assert data["bonobot_agent_limit"] == -1


@pytest.mark.regression
@pytest.mark.asyncio
async def test_admin_tier_pro_syncs_bonobot(client, test_org, auth_headers):
    """
    Setting tier to 'pro' should set bonobot_plan='pro' and bonobot_agent_limit=25.
    """
    resp = await client.post(
        f"/api/admin/organizations/{test_org.id}/tier",
        json={"tier": "pro"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["subscription_tier"] == "pro"
    assert data["bonobot_plan"] == "pro"
    assert data["bonobot_agent_limit"] == 25


@pytest.mark.regression
@pytest.mark.asyncio
async def test_admin_tier_free_syncs_bonobot(client, test_org, auth_headers):
    """
    Setting tier to 'free' should set bonobot_plan='none' and bonobot_agent_limit=0.
    """
    resp = await client.post(
        f"/api/admin/organizations/{test_org.id}/tier",
        json={"tier": "free"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["subscription_tier"] == "free"
    assert data["bonobot_plan"] == "none"
    assert data["bonobot_agent_limit"] == 0


# ---------------------------------------------------------------------------
# 3. Feature gate — Enterprise org is not falsely blocked
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.asyncio
async def test_enterprise_org_not_blocked_by_usage_limit(test_engine):
    """
    Enterprise orgs have unlimited provider/gateway limits.
    check_usage_limit() must return at_limit=False for them.
    """
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        org = Organization(
            name="Enterprise Org",
            subscription_tier="enterprise",
            subscription_status="active",
        )
        session.add(org)
        await session.commit()
        await session.refresh(org)

        from app.services.feature_gate import FeatureGateService

        gate = FeatureGateService()

        # providers limit
        result = await gate.check_usage_limit(session, str(org.id), "providers")
        assert result["at_limit"] is False, "Enterprise org should never be at provider limit"
        assert result["remaining"] == float("inf")

        # members limit
        result = await gate.check_usage_limit(session, str(org.id), "members")
        assert result["at_limit"] is False, "Enterprise org should never be at member limit"


# ---------------------------------------------------------------------------
# 4. Bonobot plan dropdown sync — changing bonobot_plan auto-syncs limit
# ---------------------------------------------------------------------------

@pytest.mark.regression
@pytest.mark.asyncio
async def test_bonobot_plan_change_syncs_agent_limit(client, test_org, auth_headers):
    """
    When bonobot_plan is changed directly (without changing tier), the
    bonobot_agent_limit should auto-sync.
    """
    # Set bonobot_plan to enterprise
    resp = await client.post(
        f"/api/admin/organizations/{test_org.id}/tier",
        json={"bonobot_plan": "enterprise"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["bonobot_plan"] == "enterprise"
    assert data["bonobot_agent_limit"] == -1

    # Set bonobot_plan to pro
    resp = await client.post(
        f"/api/admin/organizations/{test_org.id}/tier",
        json={"bonobot_plan": "pro"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["bonobot_plan"] == "pro"
    assert data["bonobot_agent_limit"] == 25

    # Set bonobot_plan to none
    resp = await client.post(
        f"/api/admin/organizations/{test_org.id}/tier",
        json={"bonobot_plan": "none"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["bonobot_plan"] == "none"
    assert data["bonobot_agent_limit"] == 0
