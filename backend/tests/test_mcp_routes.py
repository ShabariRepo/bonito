"""
Tests for MCP Server API routes.

Covers:
  - CRUD operations (create, list, get, update, delete)
  - Test connection endpoint
  - Template listing
  - Auth config redaction
  - Validation
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.agent import Agent
from app.models.agent_mcp_server import AgentMCPServer
from app.models.project import Project


@pytest_asyncio.fixture
async def project(test_engine, test_org) -> Project:
    """Create a Project for MCP route tests."""
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        proj = Project(
            org_id=test_org.id,
            name="MCP Test Project",
            budget_monthly=Decimal("100.00"),
            budget_spent=Decimal("0.00"),
        )
        session.add(proj)
        await session.commit()
        await session.refresh(proj)
        return proj


@pytest_asyncio.fixture
async def agent(test_engine, test_org, project) -> Agent:
    """Create a test agent."""
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        a = Agent(
            project_id=project.id,
            org_id=test_org.id,
            name="MCP Test Agent",
            system_prompt="Test agent for MCP routes.",
            model_id="gpt-4o",
            tool_policy={"mode": "all"},
            status="active",
        )
        session.add(a)
        await session.commit()
        await session.refresh(a)
        return a


@pytest_asyncio.fixture
async def mcp_server(test_engine, test_org, agent) -> AgentMCPServer:
    """Create a test MCP server."""
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        server = AgentMCPServer(
            agent_id=agent.id,
            org_id=test_org.id,
            name="Test S3 Server",
            transport_type="stdio",
            endpoint_config={"command": "npx", "args": ["-y", "@aws/mcp-server-s3"]},
            auth_config={"type": "none"},
            enabled=True,
            discovered_tools=[
                {"name": "list_buckets", "description": "List S3 buckets", "input_schema": {}},
            ],
            last_connected_at=datetime.now(timezone.utc),
        )
        session.add(server)
        await session.commit()
        await session.refresh(server)
        return server


class TestMCPServerCRUD:
    """Tests for MCP server CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_mcp_server_stdio(self, auth_client: AsyncClient, agent):
        """POST creates a stdio MCP server."""
        response = await auth_client.post(
            f"/api/agents/{agent.id}/mcp-servers",
            json={
                "name": "AWS S3",
                "transport_type": "stdio",
                "endpoint_config": {
                    "command": "npx",
                    "args": ["-y", "@aws/mcp-server-s3"],
                    "env": {"AWS_REGION": "us-east-1"},
                },
                "auth_config": {"type": "none"},
                "enabled": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "AWS S3"
        assert data["transport_type"] == "stdio"
        assert data["enabled"] is True
        assert data["endpoint_config"]["command"] == "npx"

    @pytest.mark.asyncio
    async def test_create_mcp_server_http(self, auth_client: AsyncClient, agent):
        """POST creates an HTTP MCP server."""
        response = await auth_client.post(
            f"/api/agents/{agent.id}/mcp-servers",
            json={
                "name": "Remote MCP",
                "transport_type": "http",
                "endpoint_config": {"url": "https://mcp.example.com/api"},
                "auth_config": {"type": "bearer_token", "token": "secret123"},
                "enabled": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Remote MCP"
        assert data["transport_type"] == "http"
        # Auth should be redacted
        assert data["auth_config"]["type"] == "bearer_token"
        assert data["auth_config"]["configured"] is True
        assert "token" not in data["auth_config"]  # Redacted

    @pytest.mark.asyncio
    async def test_create_mcp_server_with_template(self, auth_client: AsyncClient, agent):
        """POST with template_id fills in defaults."""
        response = await auth_client.post(
            f"/api/agents/{agent.id}/mcp-servers",
            json={
                "name": "AWS S3",
                "transport_type": "stdio",
                "endpoint_config": {},
                "template_id": "aws-s3",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["endpoint_config"]["command"] == "npx"

    @pytest.mark.asyncio
    async def test_create_mcp_server_stdio_missing_command(self, auth_client: AsyncClient, agent):
        """POST with stdio transport but no command returns 400."""
        response = await auth_client.post(
            f"/api/agents/{agent.id}/mcp-servers",
            json={
                "name": "Bad Config",
                "transport_type": "stdio",
                "endpoint_config": {},
            },
        )
        assert response.status_code == 400
        body = response.json()
        msg = body.get("detail", "") or body.get("error", {}).get("message", "")
        assert "command" in msg.lower()

    @pytest.mark.asyncio
    async def test_create_mcp_server_http_missing_url(self, auth_client: AsyncClient, agent):
        """POST with http transport but no url returns 400."""
        response = await auth_client.post(
            f"/api/agents/{agent.id}/mcp-servers",
            json={
                "name": "Bad HTTP Config",
                "transport_type": "http",
                "endpoint_config": {},
            },
        )
        assert response.status_code == 400
        body = response.json()
        msg = body.get("detail", "") or body.get("error", {}).get("message", "")
        assert "url" in msg.lower()

    @pytest.mark.asyncio
    async def test_create_mcp_server_invalid_agent(self, auth_client: AsyncClient):
        """POST to non-existent agent returns 404."""
        fake_id = uuid.uuid4()
        response = await auth_client.post(
            f"/api/agents/{fake_id}/mcp-servers",
            json={
                "name": "Test",
                "transport_type": "stdio",
                "endpoint_config": {"command": "echo"},
            },
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_mcp_servers(self, auth_client: AsyncClient, agent, mcp_server):
        """GET lists MCP servers for an agent."""
        response = await auth_client.get(f"/api/agents/{agent.id}/mcp-servers")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["name"] == "Test S3 Server"

    @pytest.mark.asyncio
    async def test_get_mcp_server(self, auth_client: AsyncClient, agent, mcp_server):
        """GET returns MCP server details with discovered tools."""
        response = await auth_client.get(
            f"/api/agents/{agent.id}/mcp-servers/{mcp_server.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test S3 Server"
        assert len(data["discovered_tools"]) == 1
        assert data["discovered_tools"][0]["name"] == "list_buckets"

    @pytest.mark.asyncio
    async def test_get_mcp_server_not_found(self, auth_client: AsyncClient, agent):
        """GET returns 404 for non-existent server."""
        fake_id = uuid.uuid4()
        response = await auth_client.get(
            f"/api/agents/{agent.id}/mcp-servers/{fake_id}"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_mcp_server(self, auth_client: AsyncClient, agent, mcp_server):
        """PUT updates MCP server config."""
        response = await auth_client.put(
            f"/api/agents/{agent.id}/mcp-servers/{mcp_server.id}",
            json={"name": "Updated S3", "enabled": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated S3"
        assert data["enabled"] is False

    @pytest.mark.asyncio
    async def test_update_mcp_server_clears_cache_on_config_change(
        self, auth_client: AsyncClient, agent, mcp_server
    ):
        """PUT clears discovered_tools when endpoint_config changes."""
        response = await auth_client.put(
            f"/api/agents/{agent.id}/mcp-servers/{mcp_server.id}",
            json={"endpoint_config": {"command": "python", "args": ["new_server.py"]}},
        )
        assert response.status_code == 200
        data = response.json()
        # discovered_tools should be cleared since endpoint changed
        assert data["discovered_tools"] is None

    @pytest.mark.asyncio
    async def test_delete_mcp_server(self, auth_client: AsyncClient, agent, mcp_server):
        """DELETE removes MCP server."""
        response = await auth_client.delete(
            f"/api/agents/{agent.id}/mcp-servers/{mcp_server.id}"
        )
        assert response.status_code == 204

        # Verify it's gone
        response = await auth_client.get(
            f"/api/agents/{agent.id}/mcp-servers/{mcp_server.id}"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_toggle_server(self, auth_client: AsyncClient, agent, mcp_server):
        """PUT can toggle enabled/disabled."""
        # Disable
        response = await auth_client.put(
            f"/api/agents/{agent.id}/mcp-servers/{mcp_server.id}",
            json={"enabled": False},
        )
        assert response.status_code == 200
        assert response.json()["enabled"] is False

        # Re-enable
        response = await auth_client.put(
            f"/api/agents/{agent.id}/mcp-servers/{mcp_server.id}",
            json={"enabled": True},
        )
        assert response.status_code == 200
        assert response.json()["enabled"] is True


class TestMCPServerTest:
    """Tests for the test connection endpoint."""

    @pytest.mark.asyncio
    async def test_connection_success(self, auth_client: AsyncClient, agent, mcp_server):
        """POST /test returns success with discovered tools."""
        from app.services.mcp_client import MCPToolDefinition

        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.list_tools = AsyncMock(
            return_value=[
                MCPToolDefinition("list_buckets", "List S3 buckets", {}),
                MCPToolDefinition("get_object", "Get object", {}),
            ]
        )
        mock_client.disconnect = AsyncMock()

        with patch("app.api.routes.mcp_servers.create_mcp_client", return_value=mock_client):
            response = await auth_client.post(
                f"/api/agents/{agent.id}/mcp-servers/{mcp_server.id}/test"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected"
        assert data["tools_discovered"] == 2
        assert len(data["tools"]) == 2

    @pytest.mark.asyncio
    async def test_connection_failure(self, auth_client: AsyncClient, agent, mcp_server):
        """POST /test returns error on connection failure."""
        from app.services.mcp_client import MCPConnectionError

        mock_client = AsyncMock()
        mock_client.connect = AsyncMock(side_effect=MCPConnectionError("Connection refused"))

        with patch("app.api.routes.mcp_servers.create_mcp_client", return_value=mock_client):
            response = await auth_client.post(
                f"/api/agents/{agent.id}/mcp-servers/{mcp_server.id}/test"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Connection refused" in data["error"]


class TestMCPTemplates:
    """Tests for MCP template listing."""

    @pytest.mark.asyncio
    async def test_list_templates(self, auth_client: AsyncClient):
        """GET /mcp-templates returns all templates."""
        response = await auth_client.get("/api/mcp-templates")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 5

        # Verify structure
        template = data[0]
        assert "id" in template
        assert "name" in template
        assert "description" in template
        assert "transport_type" in template
        assert "category" in template

    @pytest.mark.asyncio
    async def test_templates_include_aws(self, auth_client: AsyncClient):
        """Templates include AWS MCP servers."""
        response = await auth_client.get("/api/mcp-templates")
        data = response.json()
        aws_templates = [t for t in data if t["category"] == "aws"]
        assert len(aws_templates) >= 3  # S3, Bedrock KB, DynamoDB, Lambda, CloudWatch

    @pytest.mark.asyncio
    async def test_templates_include_gcp(self, auth_client: AsyncClient):
        """Templates include GCP."""
        response = await auth_client.get("/api/mcp-templates")
        data = response.json()
        gcp_templates = [t for t in data if t["category"] == "gcp"]
        assert len(gcp_templates) >= 1
