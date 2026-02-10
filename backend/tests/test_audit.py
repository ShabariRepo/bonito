"""Tests for the /api/audit endpoint — real DB entries, pagination, filtering."""

import uuid

import pytest
from httpx import AsyncClient


async def _create_audit_log(test_engine, org_id, action="CREATE", resource_type="provider", user_name="Test User"):
    """Insert an audit log entry directly into the DB."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from app.models.audit import AuditLog

    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        log = AuditLog(
            org_id=org_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(uuid.uuid4()),
            details_json={"test": True},
            ip_address="127.0.0.1",
            user_name=user_name,
        )
        session.add(log)
        await session.commit()
        await session.refresh(log)
        return log


@pytest.mark.asyncio
async def test_audit_logs_empty(client: AsyncClient, auth_headers):
    resp = await client.get("/api/audit/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_audit_logs_with_entries(client: AsyncClient, auth_headers, test_engine, test_org):
    """Audit log should return real DB entries."""
    await _create_audit_log(test_engine, test_org.id, action="CREATE", resource_type="provider")
    await _create_audit_log(test_engine, test_org.id, action="DELETE", resource_type="policy")

    resp = await client.get("/api/audit/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    # Each item should have the expected structure
    for item in data["items"]:
        assert "id" in item
        assert "action" in item
        assert "resource_type" in item
        assert "created_at" in item


@pytest.mark.asyncio
async def test_audit_logs_pagination(client: AsyncClient, auth_headers, test_engine, test_org):
    """Test pagination of audit logs."""
    for i in range(5):
        await _create_audit_log(test_engine, test_org.id, action=f"ACTION_{i}")

    # Page 1, size 2
    resp = await client.get("/api/audit/?page=1&page_size=2", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2

    # Page 2
    resp2 = await client.get("/api/audit/?page=2&page_size=2", headers=auth_headers)
    data2 = resp2.json()
    assert len(data2["items"]) == 2
    assert data2["page"] == 2

    # Page 3 (last page, only 1 item)
    resp3 = await client.get("/api/audit/?page=3&page_size=2", headers=auth_headers)
    data3 = resp3.json()
    assert len(data3["items"]) == 1


@pytest.mark.asyncio
async def test_audit_logs_filter_by_action(client: AsyncClient, auth_headers, test_engine, test_org):
    await _create_audit_log(test_engine, test_org.id, action="CREATE")
    await _create_audit_log(test_engine, test_org.id, action="DELETE")
    await _create_audit_log(test_engine, test_org.id, action="CREATE")

    resp = await client.get("/api/audit/?action=CREATE", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 2
    assert all(item["action"] == "CREATE" for item in data["items"])


@pytest.mark.asyncio
async def test_audit_logs_filter_by_resource_type(client: AsyncClient, auth_headers, test_engine, test_org):
    await _create_audit_log(test_engine, test_org.id, resource_type="provider")
    await _create_audit_log(test_engine, test_org.id, resource_type="policy")
    await _create_audit_log(test_engine, test_org.id, resource_type="provider")

    resp = await client.get("/api/audit/?resource_type=policy", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["resource_type"] == "policy"


@pytest.mark.asyncio
async def test_audit_logs_filter_by_user_name(client: AsyncClient, auth_headers, test_engine, test_org):
    await _create_audit_log(test_engine, test_org.id, user_name="Alice")
    await _create_audit_log(test_engine, test_org.id, user_name="Bob")

    resp = await client.get("/api/audit/?user_name=Alice", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["user_name"] == "Alice"


@pytest.mark.asyncio
async def test_audit_logs_require_auth(client: AsyncClient):
    resp = await client.get("/api/audit/")
    assert resp.status_code == 403
