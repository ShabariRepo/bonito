"""
Tests for the MCP Client module.

Covers:
  Group 1 — MCPToolDefinition (serialization, OpenAI conversion)
  Group 2 — StdioMCPClient (connect, list_tools, call_tool, error handling)
  Group 3 — HTTPMCPClient (connect, list_tools, call_tool, auth, SSE)
  Group 4 — MCPClientManager (multi-server, routing, namespacing)
  Group 5 — Templates and utilities
  Group 6 — Agent engine MCP integration
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
import pytest_asyncio

from app.services.mcp_client import (
    MCPClient,
    MCPClientManager,
    MCPConnectionError,
    MCPError,
    MCPToolCallError,
    MCPToolDefinition,
    StdioMCPClient,
    HTTPMCPClient,
    create_mcp_client,
    get_mcp_template,
    get_mcp_templates,
    make_namespaced_tool_name,
    parse_namespaced_tool_name,
    MCP_TEMPLATES,
)


# ══════════════════════════════════════════════════════════════════
# Group 1 — MCPToolDefinition
# ══════════════════════════════════════════════════════════════════


class TestMCPToolDefinition:
    """Tests for MCPToolDefinition data class."""

    def test_to_dict(self):
        """Tool definition serializes to dict."""
        tool = MCPToolDefinition(
            name="list_buckets",
            description="List S3 buckets",
            input_schema={"type": "object", "properties": {"prefix": {"type": "string"}}},
        )
        d = tool.to_dict()
        assert d["name"] == "list_buckets"
        assert d["description"] == "List S3 buckets"
        assert d["input_schema"]["type"] == "object"

    def test_to_openai_tool(self):
        """Tool definition converts to OpenAI function-calling format."""
        tool = MCPToolDefinition(
            name="get_object",
            description="Get an S3 object",
            input_schema={
                "type": "object",
                "properties": {"bucket": {"type": "string"}, "key": {"type": "string"}},
                "required": ["bucket", "key"],
            },
        )
        openai_tool = tool.to_openai_tool("mcp_aws_s3_get_object")
        assert openai_tool["type"] == "function"
        assert openai_tool["function"]["name"] == "mcp_aws_s3_get_object"
        assert openai_tool["function"]["description"] == "Get an S3 object"
        assert "bucket" in openai_tool["function"]["parameters"]["properties"]

    def test_to_openai_tool_empty_schema(self):
        """Tool with no input schema gets default empty object."""
        tool = MCPToolDefinition(name="ping", description="Ping server", input_schema={})
        openai_tool = tool.to_openai_tool("mcp_test_ping")
        assert openai_tool["function"]["parameters"] == {"type": "object", "properties": {}}

    def test_from_mcp_response(self):
        """Parse from MCP tools/list response format."""
        data = {
            "name": "search",
            "description": "Search documents",
            "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}},
        }
        tool = MCPToolDefinition.from_mcp_response(data)
        assert tool.name == "search"
        assert tool.description == "Search documents"
        assert "query" in tool.input_schema["properties"]

    def test_from_mcp_response_snake_case(self):
        """Parse from MCP response with snake_case key (fallback)."""
        data = {
            "name": "search",
            "description": "Search",
            "input_schema": {"type": "object", "properties": {}},
        }
        tool = MCPToolDefinition.from_mcp_response(data)
        assert tool.name == "search"
        assert tool.input_schema["type"] == "object"


# ══════════════════════════════════════════════════════════════════
# Group 2 — StdioMCPClient
# ══════════════════════════════════════════════════════════════════


class TestStdioMCPClient:
    """Tests for stdio-based MCP client."""

    @pytest.mark.asyncio
    async def test_connect_sends_initialize(self):
        """Client sends initialize request on connect."""
        client = StdioMCPClient(
            server_name="test",
            server_id="test-id",
            command="echo",
            args=["test"],
        )

        # Mock the subprocess
        mock_process = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()
        mock_process.terminate = MagicMock()
        mock_process.wait = AsyncMock()

        # Initialize response
        init_response = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "test-server", "version": "1.0.0"},
                "capabilities": {},
            },
        }).encode() + b"\n"
        mock_process.stdout.readline = AsyncMock(return_value=init_response)
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            await client.connect()

        assert client.connected is True
        # Verify initialize was sent
        write_calls = mock_process.stdin.write.call_args_list
        assert len(write_calls) >= 1
        first_write = json.loads(write_calls[0][0][0].decode())
        assert first_write["method"] == "initialize"

    @pytest.mark.asyncio
    async def test_connect_command_not_found(self):
        """FileNotFoundError raises MCPConnectionError."""
        client = StdioMCPClient(
            server_name="nonexistent",
            server_id="test-id",
            command="nonexistent_binary_xyz",
        )

        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError()):
            with pytest.raises(MCPConnectionError, match="not found"):
                await client.connect()

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """list_tools parses tools/list response."""
        client = StdioMCPClient(
            server_name="test",
            server_id="test-id",
            command="echo",
        )
        client._connected = True

        tools_response = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {
                        "name": "list_buckets",
                        "description": "List S3 buckets",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                    {
                        "name": "get_object",
                        "description": "Get S3 object",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"key": {"type": "string"}},
                        },
                    },
                ]
            },
        }).encode() + b"\n"

        mock_process = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=tools_response)
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        client._process = mock_process

        tools = await client.list_tools()
        assert len(tools) == 2
        assert tools[0].name == "list_buckets"
        assert tools[1].name == "get_object"

    @pytest.mark.asyncio
    async def test_call_tool_text_content(self):
        """call_tool extracts text content from MCP response."""
        client = StdioMCPClient(
            server_name="test",
            server_id="test-id",
            command="echo",
        )
        client._connected = True

        tool_response = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [
                    {"type": "text", "text": "Found 3 buckets: data, logs, backups"}
                ]
            },
        }).encode() + b"\n"

        mock_process = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=tool_response)
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        client._process = mock_process

        result = await client.call_tool("list_buckets", {})
        assert "Found 3 buckets" in result["result"]

    @pytest.mark.asyncio
    async def test_call_tool_error_response(self):
        """call_tool raises MCPToolCallError on error response."""
        client = StdioMCPClient(
            server_name="test",
            server_id="test-id",
            command="echo",
        )
        client._connected = True

        error_response = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32000, "message": "Access denied"},
        }).encode() + b"\n"

        mock_process = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=error_response)
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        client._process = mock_process

        with pytest.raises(MCPToolCallError, match="Access denied"):
            await client.call_tool("protected_tool", {})

    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self):
        """call_tool raises MCPError when not connected."""
        client = StdioMCPClient(
            server_name="test",
            server_id="test-id",
            command="echo",
        )
        # Not connected
        with pytest.raises(MCPError, match="Not connected"):
            await client.call_tool("any_tool", {})

    @pytest.mark.asyncio
    async def test_disconnect_terminates_process(self):
        """disconnect kills the subprocess."""
        client = StdioMCPClient(
            server_name="test",
            server_id="test-id",
            command="echo",
        )
        client._connected = True

        mock_process = AsyncMock()
        mock_process.terminate = MagicMock()
        mock_process.wait = AsyncMock()
        client._process = mock_process

        await client.disconnect()
        assert client.connected is False
        mock_process.terminate.assert_called_once()


# ══════════════════════════════════════════════════════════════════
# Group 3 — HTTPMCPClient
# ══════════════════════════════════════════════════════════════════


class TestHTTPMCPClient:
    """Tests for HTTP-based MCP client."""

    @pytest.mark.asyncio
    async def test_connect_sends_initialize(self):
        """HTTP client sends initialize request."""
        client = HTTPMCPClient(
            server_name="remote",
            server_id="remote-id",
            url="https://mcp.example.com/api",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "remote-server"},
                "capabilities": {},
            },
        }
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        mock_http_client.aclose = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            await client.connect()

        assert client.connected is True

    @pytest.mark.asyncio
    async def test_auth_bearer_token(self):
        """Bearer token auth adds Authorization header."""
        client = HTTPMCPClient(
            server_name="auth-test",
            server_id="auth-id",
            url="https://mcp.example.com/api",
            auth_config={"type": "bearer_token", "token": "my-secret-token"},
        )

        headers = client._build_auth_headers()
        assert headers["Authorization"] == "Bearer my-secret-token"

    @pytest.mark.asyncio
    async def test_auth_api_key(self):
        """API key auth adds custom header."""
        client = HTTPMCPClient(
            server_name="auth-test",
            server_id="auth-id",
            url="https://mcp.example.com/api",
            auth_config={"type": "api_key", "header": "X-Custom-Key", "key": "abc123"},
        )

        headers = client._build_auth_headers()
        assert headers["X-Custom-Key"] == "abc123"

    @pytest.mark.asyncio
    async def test_auth_none(self):
        """No auth produces empty headers."""
        client = HTTPMCPClient(
            server_name="no-auth",
            server_id="no-auth-id",
            url="https://mcp.example.com/api",
            auth_config={"type": "none"},
        )

        headers = client._build_auth_headers()
        assert headers == {}

    def test_parse_sse_response(self):
        """SSE response parsing extracts JSON-RPC data."""
        client = HTTPMCPClient(
            server_name="sse-test",
            server_id="sse-id",
            url="https://mcp.example.com/sse",
        )

        sse_text = 'data: {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}\n\n'
        result = client._parse_sse_response(sse_text)
        assert result["jsonrpc"] == "2.0"
        assert result["result"]["tools"] == []

    @pytest.mark.asyncio
    async def test_connect_auth_failure(self):
        """HTTP 401 raises MCPConnectionError."""
        client = HTTPMCPClient(
            server_name="bad-auth",
            server_id="bad-auth-id",
            url="https://mcp.example.com/api",
        )

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.headers = {"content-type": "application/json"}

        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)
        mock_http_client.aclose = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            with pytest.raises(MCPConnectionError, match="Authentication failed"):
                await client.connect()


# ══════════════════════════════════════════════════════════════════
# Group 4 — MCPClientManager
# ══════════════════════════════════════════════════════════════════


class TestMCPClientManager:
    """Tests for MCPClientManager multi-server management."""

    @pytest.mark.asyncio
    async def test_connect_servers_discovers_tools(self):
        """Manager connects to servers and discovers all tools."""
        manager = MCPClientManager()

        # Mock create_mcp_client to return fake clients
        mock_client_1 = AsyncMock(spec=MCPClient)
        mock_client_1.connected = True
        mock_client_1.tools = [
            MCPToolDefinition("list_buckets", "List buckets", {}),
            MCPToolDefinition("get_object", "Get object", {}),
        ]
        mock_client_1.connect = AsyncMock()
        mock_client_1.list_tools = AsyncMock(return_value=mock_client_1.tools)
        mock_client_1.disconnect = AsyncMock()

        mock_client_2 = AsyncMock(spec=MCPClient)
        mock_client_2.connected = True
        mock_client_2.tools = [
            MCPToolDefinition("search", "Search docs", {}),
        ]
        mock_client_2.connect = AsyncMock()
        mock_client_2.list_tools = AsyncMock(return_value=mock_client_2.tools)
        mock_client_2.disconnect = AsyncMock()

        clients = {"server-1": mock_client_1, "server-2": mock_client_2}
        call_count = {"n": 0}

        def mock_create(server_name, server_id, transport_type, endpoint_config, auth_config=None):
            return clients[server_id]

        servers = [
            {"id": "server-1", "name": "aws-s3", "transport_type": "stdio", "endpoint_config": {"command": "npx"}},
            {"id": "server-2", "name": "search", "transport_type": "http", "endpoint_config": {"url": "https://example.com"}},
        ]

        with patch("app.services.mcp_client.create_mcp_client", side_effect=mock_create):
            tools = await manager.connect_servers(servers)

        assert len(tools) == 3
        tool_names = [t.name for t in tools]
        assert "mcp_aws_s3_list_buckets" in tool_names
        assert "mcp_aws_s3_get_object" in tool_names
        assert "mcp_search_search" in tool_names

    @pytest.mark.asyncio
    async def test_connect_servers_skips_failed(self):
        """Manager gracefully skips servers that fail to connect."""
        manager = MCPClientManager()

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.connect = AsyncMock(side_effect=MCPConnectionError("refused"))

        def mock_create(*args, **kwargs):
            return mock_client

        servers = [
            {"id": "s1", "name": "bad-server", "transport_type": "stdio", "endpoint_config": {"command": "nope"}},
        ]

        with patch("app.services.mcp_client.create_mcp_client", side_effect=mock_create):
            tools = await manager.connect_servers(servers)

        assert len(tools) == 0
        assert len(manager.connected_servers) == 0

    @pytest.mark.asyncio
    async def test_call_tool_routes_correctly(self):
        """Tool calls are routed to the correct MCP server."""
        manager = MCPClientManager()

        # Manually set up internal state
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_client.call_tool = AsyncMock(return_value={"result": "bucket-data"})
        manager._clients["server-1"] = mock_client
        manager._tool_map["mcp_aws_s3_list_buckets"] = ("server-1", "list_buckets")

        result = await manager.call_tool("mcp_aws_s3_list_buckets", {})
        assert result == {"result": "bucket-data"}
        mock_client.call_tool.assert_called_once_with("list_buckets", {})

    @pytest.mark.asyncio
    async def test_call_tool_unknown(self):
        """Unknown tool returns error."""
        manager = MCPClientManager()
        result = await manager.call_tool("mcp_unknown_tool", {})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_call_tool_disconnected_server(self):
        """Tool call to disconnected server returns error."""
        manager = MCPClientManager()
        mock_client = AsyncMock()
        mock_client.connected = False
        manager._clients["server-1"] = mock_client
        manager._tool_map["mcp_test_tool"] = ("server-1", "tool")

        result = await manager.call_tool("mcp_test_tool", {})
        assert "error" in result

    def test_is_mcp_tool(self):
        """is_mcp_tool checks tool_map."""
        manager = MCPClientManager()
        manager._tool_map["mcp_s3_list"] = ("s1", "list")
        assert manager.is_mcp_tool("mcp_s3_list") is True
        assert manager.is_mcp_tool("get_current_time") is False

    def test_get_server_id_for_tool(self):
        """get_server_id_for_tool returns correct server."""
        manager = MCPClientManager()
        manager._tool_map["mcp_s3_list"] = ("server-1", "list")
        assert manager.get_server_id_for_tool("mcp_s3_list") == "server-1"
        assert manager.get_server_id_for_tool("unknown") is None

    def test_get_original_tool_name(self):
        """get_original_tool_name returns un-namespaced name."""
        manager = MCPClientManager()
        manager._tool_map["mcp_s3_list"] = ("server-1", "list")
        assert manager.get_original_tool_name("mcp_s3_list") == "list"

    @pytest.mark.asyncio
    async def test_disconnect_all(self):
        """disconnect_all closes all clients and clears state."""
        manager = MCPClientManager()
        mock_client = AsyncMock()
        mock_client.disconnect = AsyncMock()
        manager._clients["s1"] = mock_client
        manager._tool_map["mcp_test"] = ("s1", "test")

        await manager.disconnect_all()
        assert len(manager._clients) == 0
        assert len(manager._tool_map) == 0
        mock_client.disconnect.assert_called_once()


# ══════════════════════════════════════════════════════════════════
# Group 5 — Templates and Utilities
# ══════════════════════════════════════════════════════════════════


class TestTemplatesAndUtils:
    """Tests for MCP templates and utility functions."""

    def test_make_namespaced_tool_name(self):
        """Tool names are correctly namespaced."""
        assert make_namespaced_tool_name("aws-s3", "list_buckets") == "mcp_aws_s3_list_buckets"
        assert make_namespaced_tool_name("My Server", "search") == "mcp_my_server_search"
        assert make_namespaced_tool_name("github.com", "get_repo") == "mcp_github_com_get_repo"

    def test_parse_namespaced_tool_name(self):
        """Namespaced names are correctly parsed."""
        result = parse_namespaced_tool_name("mcp_aws_s3_list_buckets")
        assert result is not None
        assert result[0] == "unknown"  # best-effort

        result = parse_namespaced_tool_name("get_current_time")
        assert result is None  # Not an MCP tool

    def test_create_mcp_client_stdio(self):
        """Factory creates StdioMCPClient for stdio transport."""
        client = create_mcp_client(
            server_name="test",
            server_id="id",
            transport_type="stdio",
            endpoint_config={"command": "npx", "args": ["-y", "test"]},
        )
        assert isinstance(client, StdioMCPClient)

    def test_create_mcp_client_http(self):
        """Factory creates HTTPMCPClient for http transport."""
        client = create_mcp_client(
            server_name="test",
            server_id="id",
            transport_type="http",
            endpoint_config={"url": "https://example.com"},
        )
        assert isinstance(client, HTTPMCPClient)

    def test_create_mcp_client_invalid_transport(self):
        """Factory raises ValueError for unknown transport."""
        with pytest.raises(ValueError, match="Unknown MCP transport"):
            create_mcp_client(
                server_name="test",
                server_id="id",
                transport_type="grpc",
                endpoint_config={},
            )

    def test_get_mcp_templates_returns_all(self):
        """get_mcp_templates returns all templates."""
        templates = get_mcp_templates()
        assert len(templates) >= 5  # At least AWS templates + GCP + Azure
        assert "aws-s3" in templates
        assert "gcp-vertex-search" in templates
        assert "azure-ai-foundry" in templates

    def test_get_mcp_template_exists(self):
        """get_mcp_template returns template by ID."""
        template = get_mcp_template("aws-s3")
        assert template is not None
        assert template["name"] == "AWS S3"
        assert template["transport_type"] == "stdio"

    def test_get_mcp_template_not_found(self):
        """get_mcp_template returns None for unknown ID."""
        assert get_mcp_template("nonexistent") is None

    def test_all_templates_have_required_fields(self):
        """Every template has all required fields."""
        for tid, template in MCP_TEMPLATES.items():
            assert "name" in template, f"Template {tid} missing 'name'"
            assert "description" in template, f"Template {tid} missing 'description'"
            assert "transport_type" in template, f"Template {tid} missing 'transport_type'"
            assert template["transport_type"] in ("stdio", "http"), f"Template {tid} has invalid transport"
            assert "endpoint_config" in template, f"Template {tid} missing 'endpoint_config'"
            assert "category" in template, f"Template {tid} missing 'category'"

    def test_aws_templates_are_stdio(self):
        """AWS templates use stdio transport."""
        for tid, template in MCP_TEMPLATES.items():
            if template["category"] == "aws":
                assert template["transport_type"] == "stdio", f"AWS template {tid} should be stdio"


# ══════════════════════════════════════════════════════════════════
# Group 6 — Agent Engine MCP Integration
# ══════════════════════════════════════════════════════════════════


class TestAgentEngineMCPIntegration:
    """Tests for MCP integration in the agent engine."""

    def test_is_tool_allowed_mcp_mode_all(self):
        """MCP tools are allowed in mode 'all'."""
        from app.services.agent_engine import AgentEngine

        engine = AgentEngine()
        agent_mock = MagicMock()
        agent_mock.tool_policy = {"mode": "all"}

        assert engine._is_tool_allowed(agent_mock, "mcp_aws_s3_list_buckets") is True
        assert engine._is_tool_allowed(agent_mock, "mcp_custom_tool") is True

    def test_is_tool_allowed_mcp_mode_none(self):
        """MCP tools are blocked in mode 'none'."""
        from app.services.agent_engine import AgentEngine

        engine = AgentEngine()
        agent_mock = MagicMock()
        agent_mock.tool_policy = {"mode": "none"}

        assert engine._is_tool_allowed(agent_mock, "mcp_aws_s3_list_buckets") is False

    def test_is_tool_allowed_mcp_mode_allowlist(self):
        """MCP tools can be individually allowed in allowlist mode."""
        from app.services.agent_engine import AgentEngine

        engine = AgentEngine()
        agent_mock = MagicMock()
        agent_mock.tool_policy = {
            "mode": "allowlist",
            "allowed": ["mcp_aws_s3_list_buckets", "get_current_time"],
        }

        assert engine._is_tool_allowed(agent_mock, "mcp_aws_s3_list_buckets") is True
        assert engine._is_tool_allowed(agent_mock, "mcp_aws_s3_get_object") is False
        assert engine._is_tool_allowed(agent_mock, "get_current_time") is True

    def test_is_tool_allowed_mcp_mode_denylist(self):
        """MCP tools work with denylist mode."""
        from app.services.agent_engine import AgentEngine

        engine = AgentEngine()
        agent_mock = MagicMock()
        agent_mock.tool_policy = {
            "mode": "denylist",
            "denied": ["mcp_aws_s3_delete_object"],
        }

        assert engine._is_tool_allowed(agent_mock, "mcp_aws_s3_list_buckets") is True
        assert engine._is_tool_allowed(agent_mock, "mcp_aws_s3_delete_object") is False
