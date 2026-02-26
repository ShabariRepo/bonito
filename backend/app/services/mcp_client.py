"""
MCP (Model Context Protocol) Client for Bonobot Agents

Provides async MCP client that connects to MCP servers via stdio (subprocess)
or HTTP/SSE transport. Handles tool discovery, tool execution, authentication,
and connection lifecycle management.

Usage:
    manager = MCPClientManager()
    async with manager.connect(server_config) as client:
        tools = await client.list_tools()
        result = await client.call_tool("tool_name", {"arg": "value"})
"""

import asyncio
import json
import logging
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Timeouts
STDIO_STARTUP_TIMEOUT = 10  # seconds to wait for stdio server to start
HTTP_CONNECT_TIMEOUT = 30  # seconds for HTTP connection
HTTP_READ_TIMEOUT = 60  # seconds for HTTP read
TOOL_CALL_TIMEOUT = 60  # seconds per tool call


class MCPError(Exception):
    """Base exception for MCP operations."""
    pass


class MCPConnectionError(MCPError):
    """Failed to connect to MCP server."""
    pass


class MCPToolCallError(MCPError):
    """Failed to execute a tool call."""
    pass


class MCPToolDefinition:
    """Represents a tool discovered from an MCP server."""

    def __init__(self, name: str, description: str, input_schema: Dict[str, Any]):
        self.name = name
        self.description = description
        self.input_schema = input_schema

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    def to_openai_tool(self, namespaced_name: str) -> Dict[str, Any]:
        """Convert to OpenAI function-calling tool format."""
        return {
            "type": "function",
            "function": {
                "name": namespaced_name,
                "description": self.description,
                "parameters": self.input_schema or {"type": "object", "properties": {}},
            },
        }

    @classmethod
    def from_mcp_response(cls, tool_data: Dict[str, Any]) -> "MCPToolDefinition":
        return cls(
            name=tool_data.get("name", ""),
            description=tool_data.get("description", ""),
            input_schema=tool_data.get("inputSchema", tool_data.get("input_schema", {})),
        )


class MCPClient:
    """Base class for MCP client connections."""

    def __init__(self, server_name: str, server_id: str):
        self.server_name = server_name
        self.server_id = server_id
        self._tools: List[MCPToolDefinition] = []
        self._connected = False
        self._request_id = 0

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def tools(self) -> List[MCPToolDefinition]:
        return self._tools

    def _next_request_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _build_jsonrpc_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build a JSON-RPC 2.0 request."""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": method,
        }
        if params is not None:
            request["params"] = params
        return request

    async def connect(self) -> None:
        raise NotImplementedError

    async def disconnect(self) -> None:
        raise NotImplementedError

    async def list_tools(self) -> List[MCPToolDefinition]:
        raise NotImplementedError

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class StdioMCPClient(MCPClient):
    """MCP client that communicates with a server via stdio (subprocess).

    The server is started as a child process. Communication happens via
    JSON-RPC 2.0 over stdin/stdout.
    """

    def __init__(
        self,
        server_name: str,
        server_id: str,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
    ):
        super().__init__(server_name, server_id)
        self._command = command
        self._args = args or []
        self._env = env
        self._cwd = cwd
        self._process: Optional[asyncio.subprocess.Process] = None
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()

    async def connect(self) -> None:
        """Start the MCP server subprocess and initialize the connection."""
        try:
            import os
            process_env = {**os.environ}
            if self._env:
                process_env.update(self._env)

            self._process = await asyncio.create_subprocess_exec(
                self._command,
                *self._args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
                cwd=self._cwd,
            )

            # Send initialize request
            init_request = self._build_jsonrpc_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "bonito-agent-engine",
                    "version": "1.0.0",
                },
            })
            init_response = await self._send_request(init_request)

            if "error" in init_response:
                raise MCPConnectionError(
                    f"MCP initialize failed: {init_response['error']}"
                )

            # Send initialized notification
            await self._send_notification("notifications/initialized")

            self._connected = True
            logger.info(f"MCP stdio client connected: {self.server_name}")

        except asyncio.TimeoutError:
            await self._cleanup_process()
            raise MCPConnectionError(
                f"Timeout starting MCP server '{self.server_name}' "
                f"(command: {self._command} {' '.join(self._args)})"
            )
        except FileNotFoundError:
            raise MCPConnectionError(
                f"MCP server command not found: {self._command}"
            )
        except Exception as e:
            await self._cleanup_process()
            raise MCPConnectionError(
                f"Failed to start MCP server '{self.server_name}': {e}"
            )

    async def disconnect(self) -> None:
        """Shut down the MCP server subprocess."""
        self._connected = False
        await self._cleanup_process()
        logger.info(f"MCP stdio client disconnected: {self.server_name}")

    async def list_tools(self) -> List[MCPToolDefinition]:
        """Discover tools from the MCP server via tools/list."""
        if not self._connected:
            raise MCPError("Not connected to MCP server")

        request = self._build_jsonrpc_request("tools/list")
        response = await self._send_request(request)

        if "error" in response:
            raise MCPError(f"tools/list failed: {response['error']}")

        result = response.get("result", {})
        tools_data = result.get("tools", [])
        self._tools = [MCPToolDefinition.from_mcp_response(t) for t in tools_data]
        return self._tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call via tools/call."""
        if not self._connected:
            raise MCPError("Not connected to MCP server")

        request = self._build_jsonrpc_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })

        try:
            response = await asyncio.wait_for(
                self._send_request(request),
                timeout=TOOL_CALL_TIMEOUT,
            )
        except asyncio.TimeoutError:
            raise MCPToolCallError(
                f"Tool call '{tool_name}' timed out after {TOOL_CALL_TIMEOUT}s"
            )

        if "error" in response:
            raise MCPToolCallError(
                f"Tool call '{tool_name}' failed: {response['error']}"
            )

        result = response.get("result", {})
        # MCP tools return content as a list of content blocks
        content = result.get("content", [])
        if content and isinstance(content, list):
            # Extract text content
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            return {"result": "\n".join(text_parts) if text_parts else json.dumps(content)}

        return {"result": json.dumps(result)}

    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request and read the response."""
        if not self._process or not self._process.stdin or not self._process.stdout:
            raise MCPError("Process not running")

        request_bytes = (json.dumps(request) + "\n").encode("utf-8")

        async with self._write_lock:
            self._process.stdin.write(request_bytes)
            await self._process.stdin.drain()

        async with self._read_lock:
            try:
                line = await asyncio.wait_for(
                    self._process.stdout.readline(),
                    timeout=TOOL_CALL_TIMEOUT,
                )
                if not line:
                    raise MCPError("MCP server closed stdout")
                return json.loads(line.decode("utf-8").strip())
            except json.JSONDecodeError as e:
                raise MCPError(f"Invalid JSON from MCP server: {e}")

    async def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        if not self._process or not self._process.stdin:
            return

        notification: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params:
            notification["params"] = params

        notification_bytes = (json.dumps(notification) + "\n").encode("utf-8")
        async with self._write_lock:
            self._process.stdin.write(notification_bytes)
            await self._process.stdin.drain()

    async def _cleanup_process(self) -> None:
        """Kill the subprocess if running."""
        if self._process:
            try:
                self._process.terminate()
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    self._process.kill()
            except ProcessLookupError:
                pass
            self._process = None


class HTTPMCPClient(MCPClient):
    """MCP client that communicates with a server via HTTP/SSE.

    Supports streamable HTTP transport (POST requests with JSON-RPC).
    Falls back to SSE for servers that use the older SSE transport.
    """

    def __init__(
        self,
        server_name: str,
        server_id: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        auth_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(server_name, server_id)
        self._url = url
        self._headers = headers or {}
        self._auth_config = auth_config or {"type": "none"}
        self._http_client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        """Initialize HTTP client and send MCP initialize request."""
        try:
            auth_headers = self._build_auth_headers()
            all_headers = {**self._headers, **auth_headers}

            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=HTTP_CONNECT_TIMEOUT,
                    read=HTTP_READ_TIMEOUT,
                    write=30.0,
                    pool=30.0,
                ),
                headers=all_headers,
            )

            # Send initialize request
            init_request = self._build_jsonrpc_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "bonito-agent-engine",
                    "version": "1.0.0",
                },
            })
            init_response = await self._send_request(init_request)

            if "error" in init_response:
                raise MCPConnectionError(
                    f"MCP initialize failed: {init_response['error']}"
                )

            # Send initialized notification
            await self._send_notification("notifications/initialized")

            self._connected = True
            logger.info(f"MCP HTTP client connected: {self.server_name} ({self._url})")

        except httpx.ConnectError as e:
            await self._cleanup_client()
            raise MCPConnectionError(
                f"Cannot connect to MCP server '{self.server_name}' at {self._url}: {e}"
            )
        except httpx.TimeoutException:
            await self._cleanup_client()
            raise MCPConnectionError(
                f"Timeout connecting to MCP server '{self.server_name}' at {self._url}"
            )
        except MCPConnectionError:
            await self._cleanup_client()
            raise
        except Exception as e:
            await self._cleanup_client()
            raise MCPConnectionError(
                f"Failed to connect to MCP server '{self.server_name}': {e}"
            )

    async def disconnect(self) -> None:
        """Close the HTTP client."""
        self._connected = False
        await self._cleanup_client()
        logger.info(f"MCP HTTP client disconnected: {self.server_name}")

    async def list_tools(self) -> List[MCPToolDefinition]:
        """Discover tools from the MCP server via tools/list."""
        if not self._connected:
            raise MCPError("Not connected to MCP server")

        request = self._build_jsonrpc_request("tools/list")
        response = await self._send_request(request)

        if "error" in response:
            raise MCPError(f"tools/list failed: {response['error']}")

        result = response.get("result", {})
        tools_data = result.get("tools", [])
        self._tools = [MCPToolDefinition.from_mcp_response(t) for t in tools_data]
        return self._tools

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call via tools/call."""
        if not self._connected:
            raise MCPError("Not connected to MCP server")

        request = self._build_jsonrpc_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })

        try:
            response = await self._send_request(request)
        except httpx.TimeoutException:
            raise MCPToolCallError(
                f"Tool call '{tool_name}' timed out after {HTTP_READ_TIMEOUT}s"
            )

        if "error" in response:
            raise MCPToolCallError(
                f"Tool call '{tool_name}' failed: {response['error']}"
            )

        result = response.get("result", {})
        content = result.get("content", [])
        if content and isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            return {"result": "\n".join(text_parts) if text_parts else json.dumps(content)}

        return {"result": json.dumps(result)}

    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request via HTTP POST."""
        if not self._http_client:
            raise MCPError("HTTP client not initialized")

        response = await self._http_client.post(
            self._url,
            json=request,
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 401 or response.status_code == 403:
            raise MCPConnectionError(
                f"Authentication failed for MCP server '{self.server_name}' "
                f"(HTTP {response.status_code})"
            )

        response.raise_for_status()

        # Handle potential SSE response format
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            return self._parse_sse_response(response.text)

        return response.json()

    async def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a JSON-RPC notification via HTTP POST."""
        if not self._http_client:
            return

        notification: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params:
            notification["params"] = params

        try:
            await self._http_client.post(
                self._url,
                json=notification,
                headers={"Content-Type": "application/json"},
            )
        except Exception:
            pass  # Notifications are fire-and-forget

    def _parse_sse_response(self, text: str) -> Dict[str, Any]:
        """Parse SSE response to extract JSON-RPC response."""
        for line in text.strip().split("\n"):
            if line.startswith("data: "):
                data = line[6:]
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    continue
        return {"error": {"code": -1, "message": "No valid JSON-RPC response in SSE stream"}}

    def _build_auth_headers(self) -> Dict[str, str]:
        """Build authentication headers from auth_config."""
        auth_type = self._auth_config.get("type", "none")

        if auth_type == "bearer_token":
            token = self._auth_config.get("token", "")
            return {"Authorization": f"Bearer {token}"}
        elif auth_type == "api_key":
            header = self._auth_config.get("header", "X-API-Key")
            key = self._auth_config.get("key", "")
            return {header: key}

        return {}

    async def _cleanup_client(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


def create_mcp_client(
    server_name: str,
    server_id: str,
    transport_type: str,
    endpoint_config: Dict[str, Any],
    auth_config: Optional[Dict[str, Any]] = None,
) -> MCPClient:
    """Factory function to create the appropriate MCP client.

    Args:
        server_name: Human-readable server name
        server_id: UUID string of the AgentMCPServer record
        transport_type: "stdio" or "http"
        endpoint_config: Transport-specific configuration
        auth_config: Authentication configuration

    Returns:
        MCPClient instance (not yet connected)
    """
    if transport_type == "stdio":
        return StdioMCPClient(
            server_name=server_name,
            server_id=server_id,
            command=endpoint_config.get("command", ""),
            args=endpoint_config.get("args", []),
            env=endpoint_config.get("env"),
            cwd=endpoint_config.get("cwd"),
        )
    elif transport_type == "http":
        return HTTPMCPClient(
            server_name=server_name,
            server_id=server_id,
            url=endpoint_config.get("url", ""),
            headers=endpoint_config.get("headers"),
            auth_config=auth_config,
        )
    else:
        raise ValueError(f"Unknown MCP transport type: {transport_type}")


def make_namespaced_tool_name(server_name: str, tool_name: str) -> str:
    """Create a namespaced tool name to avoid collisions.

    e.g., server_name="aws-s3", tool_name="list_buckets" → "mcp_aws_s3_list_buckets"
    """
    safe_name = server_name.replace("-", "_").replace(" ", "_").replace(".", "_").lower()
    return f"mcp_{safe_name}_{tool_name}"


def parse_namespaced_tool_name(namespaced_name: str) -> Optional[tuple[str, str]]:
    """Parse a namespaced MCP tool name back into (server_name_prefix, tool_name).

    Returns None if the name doesn't match the MCP namespace pattern.
    """
    if not namespaced_name.startswith("mcp_"):
        return None
    # The format is mcp_{server}_{tool} but both server and tool can contain underscores.
    # We store the mapping in MCPClientManager so this is a best-effort parse.
    return ("unknown", namespaced_name[4:])


class MCPClientManager:
    """Manages MCP client connections for an agent session.

    Handles connecting to multiple MCP servers, tool discovery, and routing
    tool calls to the correct server.
    """

    def __init__(self):
        self._clients: Dict[str, MCPClient] = {}  # server_id → client
        self._tool_map: Dict[str, tuple[str, str]] = {}  # namespaced_name → (server_id, original_tool_name)

    async def connect_servers(
        self, servers: List[Dict[str, Any]]
    ) -> List[MCPToolDefinition]:
        """Connect to multiple MCP servers and discover all tools.

        Args:
            servers: List of server configs, each with keys:
                - id, name, transport_type, endpoint_config, auth_config

        Returns:
            Combined list of all discovered tools (namespaced).
        """
        all_tools: List[MCPToolDefinition] = []

        for server in servers:
            server_id = str(server["id"])
            server_name = server["name"]

            try:
                client = create_mcp_client(
                    server_name=server_name,
                    server_id=server_id,
                    transport_type=server["transport_type"],
                    endpoint_config=server.get("endpoint_config", {}),
                    auth_config=server.get("auth_config"),
                )

                await client.connect()
                tools = await client.list_tools()

                self._clients[server_id] = client

                # Namespace tools and build mapping
                for tool in tools:
                    namespaced = make_namespaced_tool_name(server_name, tool.name)
                    self._tool_map[namespaced] = (server_id, tool.name)
                    all_tools.append(
                        MCPToolDefinition(
                            name=namespaced,
                            description=f"[{server_name}] {tool.description}",
                            input_schema=tool.input_schema,
                        )
                    )

                logger.info(
                    f"MCP server '{server_name}' connected: {len(tools)} tools discovered"
                )

            except MCPConnectionError as e:
                logger.warning(f"Failed to connect to MCP server '{server_name}': {e}")
                continue
            except Exception as e:
                logger.warning(
                    f"Unexpected error connecting to MCP server '{server_name}': {e}"
                )
                continue

        return all_tools

    async def call_tool(self, namespaced_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route a tool call to the correct MCP server.

        Args:
            namespaced_name: The namespaced tool name (e.g., "mcp_aws_s3_list_buckets")
            arguments: Tool arguments

        Returns:
            Tool result dict
        """
        mapping = self._tool_map.get(namespaced_name)
        if not mapping:
            return {"error": f"Unknown MCP tool: {namespaced_name}"}

        server_id, original_tool_name = mapping
        client = self._clients.get(server_id)

        if not client or not client.connected:
            return {"error": f"MCP server not connected for tool: {namespaced_name}"}

        try:
            return await client.call_tool(original_tool_name, arguments)
        except MCPToolCallError as e:
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"MCP tool call failed for {namespaced_name}: {e}")
            return {"error": f"MCP tool call failed: {str(e)}"}

    def is_mcp_tool(self, tool_name: str) -> bool:
        """Check if a tool name is a registered MCP tool."""
        return tool_name in self._tool_map

    def get_server_id_for_tool(self, tool_name: str) -> Optional[str]:
        """Get the server ID for a given MCP tool name."""
        mapping = self._tool_map.get(tool_name)
        return mapping[0] if mapping else None

    def get_original_tool_name(self, namespaced_name: str) -> Optional[str]:
        """Get the original (non-namespaced) tool name."""
        mapping = self._tool_map.get(namespaced_name)
        return mapping[1] if mapping else None

    async def disconnect_all(self) -> None:
        """Disconnect all MCP clients."""
        for server_id, client in self._clients.items():
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting MCP client {server_id}: {e}")
        self._clients.clear()
        self._tool_map.clear()

    @property
    def connected_servers(self) -> List[str]:
        """List of connected server IDs."""
        return [sid for sid, c in self._clients.items() if c.connected]


# ─── Cloud MCP Templates ───

MCP_TEMPLATES = {
    "aws-s3": {
        "name": "AWS S3",
        "description": "Access Amazon S3 buckets and objects",
        "transport_type": "stdio",
        "endpoint_config": {
            "command": "npx",
            "args": ["-y", "@aws/mcp-server-s3"],
            "env": {},
        },
        "auth_config": {"type": "none"},
        "category": "aws",
    },
    "aws-bedrock-kb": {
        "name": "AWS Bedrock Knowledge Base",
        "description": "Query Amazon Bedrock Knowledge Bases for RAG",
        "transport_type": "stdio",
        "endpoint_config": {
            "command": "npx",
            "args": ["-y", "@aws/mcp-server-bedrock-kb"],
            "env": {},
        },
        "auth_config": {"type": "none"},
        "category": "aws",
    },
    "aws-dynamodb": {
        "name": "AWS DynamoDB",
        "description": "Query and manage DynamoDB tables",
        "transport_type": "stdio",
        "endpoint_config": {
            "command": "npx",
            "args": ["-y", "@aws/mcp-server-dynamodb"],
            "env": {},
        },
        "auth_config": {"type": "none"},
        "category": "aws",
    },
    "aws-lambda": {
        "name": "AWS Lambda",
        "description": "Invoke and manage Lambda functions",
        "transport_type": "stdio",
        "endpoint_config": {
            "command": "npx",
            "args": ["-y", "@aws/mcp-server-lambda"],
            "env": {},
        },
        "auth_config": {"type": "none"},
        "category": "aws",
    },
    "aws-cloudwatch": {
        "name": "AWS CloudWatch Logs",
        "description": "Query CloudWatch log groups and events",
        "transport_type": "stdio",
        "endpoint_config": {
            "command": "npx",
            "args": ["-y", "@aws/mcp-server-cloudwatch-logs"],
            "env": {},
        },
        "auth_config": {"type": "none"},
        "category": "aws",
    },
    "gcp-vertex-search": {
        "name": "GCP Vertex AI Search",
        "description": "Search and retrieve with Google Vertex AI Search",
        "transport_type": "http",
        "endpoint_config": {
            "url": "https://discoveryengine.googleapis.com/v1alpha/mcp",
            "headers": {},
        },
        "auth_config": {"type": "bearer_token", "token": ""},
        "category": "gcp",
    },
    "azure-ai-foundry": {
        "name": "Azure AI Foundry (Placeholder)",
        "description": "Azure MCP integration via Azure AI Foundry / Semantic Kernel. Note: Azure/azure-mcp was archived Feb 2026. Configure Semantic Kernel MCP client integration manually.",
        "transport_type": "http",
        "endpoint_config": {
            "url": "https://your-ai-foundry-endpoint.azure.com/mcp",
            "headers": {},
        },
        "auth_config": {"type": "bearer_token", "token": ""},
        "category": "azure",
    },
}


def get_mcp_templates() -> Dict[str, Dict[str, Any]]:
    """Return available MCP server templates."""
    return MCP_TEMPLATES


def get_mcp_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific MCP template by ID."""
    return MCP_TEMPLATES.get(template_id)
