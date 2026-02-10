"""Tests for the /api/policies endpoints (DB-backed, per-org)."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_policies_empty(client: AsyncClient, auth_headers):
    resp = await client.get("/api/policies/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_policy(client: AsyncClient, auth_headers, test_org):
    resp = await client.post("/api/policies/", headers=auth_headers, json={
        "name": "Daily spend cap",
        "type": "spend_limits",
        "rules_json": {"max_daily_spend": 100.0},
        "description": "Limit daily spend to $100",
        "enabled": True,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Daily spend cap"
    assert data["type"] == "spend_limits"
    assert data["rules_json"] == {"max_daily_spend": 100.0}
    assert data["enabled"] is True
    assert data["org_id"] == str(test_org.id)


@pytest.mark.asyncio
async def test_create_and_list_policy(client: AsyncClient, auth_headers):
    await client.post("/api/policies/", headers=auth_headers, json={
        "name": "Model access",
        "type": "model_access",
        "rules_json": {"allowed_models": ["gpt-4o"]},
    })
    resp = await client.get("/api/policies/", headers=auth_headers)
    assert resp.status_code == 200
    policies = resp.json()
    assert len(policies) >= 1
    assert any(p["name"] == "Model access" for p in policies)


@pytest.mark.asyncio
async def test_update_policy(client: AsyncClient, auth_headers):
    create_resp = await client.post("/api/policies/", headers=auth_headers, json={
        "name": "Original name",
        "type": "spend_limits",
        "rules_json": {"max_daily_spend": 50},
    })
    policy_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/policies/{policy_id}",
        headers=auth_headers,
        json={"name": "Updated name", "rules_json": {"max_daily_spend": 200}},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["name"] == "Updated name"
    assert data["rules_json"]["max_daily_spend"] == 200


@pytest.mark.asyncio
async def test_delete_policy(client: AsyncClient, auth_headers):
    create_resp = await client.post("/api/policies/", headers=auth_headers, json={
        "name": "To be deleted",
        "type": "spend_limits",
        "rules_json": {},
    })
    policy_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/policies/{policy_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # Confirm it's gone
    list_resp = await client.get("/api/policies/", headers=auth_headers)
    ids = [p["id"] for p in list_resp.json()]
    assert policy_id not in ids


@pytest.mark.asyncio
async def test_delete_nonexistent_policy(client: AsyncClient, auth_headers):
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/api/policies/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_nonexistent_policy(client: AsyncClient, auth_headers):
    fake_id = str(uuid.uuid4())
    resp = await client.patch(
        f"/api/policies/{fake_id}",
        headers=auth_headers,
        json={"name": "Nope"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_disable_policy(client: AsyncClient, auth_headers):
    create_resp = await client.post("/api/policies/", headers=auth_headers, json={
        "name": "Enabled policy",
        "type": "model_access",
        "rules_json": {"allowed_models": ["gpt-4o"]},
        "enabled": True,
    })
    policy_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/policies/{policy_id}",
        headers=auth_headers,
        json={"enabled": False},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["enabled"] is False


@pytest.mark.asyncio
async def test_policies_require_auth(client: AsyncClient):
    resp = await client.get("/api/policies/")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_spend_cap_enforcement():
    """Unit test: check_spend_cap raises PolicyViolation when cap exceeded."""
    from unittest.mock import AsyncMock, MagicMock
    from app.services.gateway import check_spend_cap, PolicyViolation
    from app.models.policy import Policy

    # Create mock DB session
    mock_db = AsyncMock()

    # Mock policy query result
    mock_policy = MagicMock(spec=Policy)
    mock_policy.org_id = uuid.uuid4()
    mock_policy.type = "spend_limits"
    mock_policy.enabled = True
    mock_policy.rules_json = {"max_daily_spend": 10.0}

    # scalar_one_or_none returns the policy
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_policy
    mock_db.execute = AsyncMock(side_effect=[
        mock_result,
        # Second execute: today's cost query returns $15 (over cap)
        MagicMock(scalar=MagicMock(return_value=15.0)),
    ])

    with pytest.raises(PolicyViolation, match="spend cap"):
        await check_spend_cap(mock_db, mock_policy.org_id)
