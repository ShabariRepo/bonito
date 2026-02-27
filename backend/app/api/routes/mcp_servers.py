"""
MCP Server Management API Routes

CRUD operations for managing MCP (Model Context Protocol) server
configurations on Bonobot agents.
"""

import time
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.agent import Agent
from app.models.agent_mcp_server import AgentMCPServer
from app.schemas.bonobot import (
    MCPServerCreate,
    MCPServerUpdate,
    MCPServerResponse,
    MCPServerTestResponse,
    MCPTemplateResponse,
)
from app.services.mcp_client import (
    create_mcp_client,
    get_mcp_templates,
    get_mcp_template,
    MCPConnectionError,
)

router = APIRouter()


def _redact_auth_config(auth_config: dict) -> dict:
    """Redact sensitive values from auth_config for API responses."""
    if not auth_config:
        return {"type": "none", "configured": False}

    auth_type = auth_config.get("type", "none")
    redacted = {"type": auth_type}

    if auth_type == "bearer_token":
        redacted["configured"] = bool(auth_config.get("token"))
    elif auth_type == "api_key":
        redacted["header"] = auth_config.get("header", "X-API-Key")
        redacted["configured"] = bool(auth_config.get("key"))
    else:
        redacted["configured"] = False

    return redacted


def _serialize_mcp_server(server: AgentMCPServer) -> MCPServerResponse:
    """Serialize an MCP server with redacted auth."""
    data = MCPServerResponse.model_validate(server)
    data.auth_config = _redact_auth_config(server.auth_config)
    return data


async def _get_agent_or_404(
    agent_id: UUID,
    org_id: UUID,
    db: AsyncSession,
) -> Agent:
    """Load agent with org check or raise 404."""
    stmt = select(Agent).where(
        and_(Agent.id == agent_id, Agent.org_id == org_id)
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return agent


# ─── CRUD Endpoints ───


@router.post(
    "/agents/{agent_id}/mcp-servers",
    response_model=MCPServerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_mcp_server(
    agent_id: UUID,
    data: MCPServerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register an MCP server for an agent."""
    agent = await _get_agent_or_404(agent_id, current_user.org_id, db)

    # If using a template, merge template defaults with provided overrides
    endpoint_config = data.endpoint_config
    auth_config = data.auth_config or {"type": "none"}
    transport_type = data.transport_type
    name = data.name

    if data.template_id:
        template = get_mcp_template(data.template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown MCP template: {data.template_id}",
            )
        # Template provides defaults; user data overrides
        transport_type = transport_type or template["transport_type"]
        name = name or template["name"]
        endpoint_config = {**template["endpoint_config"], **endpoint_config} if endpoint_config else template["endpoint_config"]
        if auth_config == {"type": "none"} and template.get("auth_config", {}).get("type") != "none":
            auth_config = template["auth_config"]

    # Validate transport-specific config
    if transport_type == "stdio":
        if not endpoint_config.get("command"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="stdio transport requires 'command' in endpoint_config",
            )
    elif transport_type == "http":
        if not endpoint_config.get("url"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="http transport requires 'url' in endpoint_config",
            )

    server = AgentMCPServer(
        agent_id=agent.id,
        org_id=current_user.org_id,
        name=name,
        transport_type=transport_type,
        endpoint_config=endpoint_config,
        auth_config=auth_config,
        enabled=data.enabled,
    )
    db.add(server)
    await db.commit()
    await db.refresh(server)

    return _serialize_mcp_server(server)


@router.get("/agents/{agent_id}/mcp-servers", response_model=List[MCPServerResponse])
async def list_mcp_servers(
    agent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List MCP servers configured for an agent."""
    await _get_agent_or_404(agent_id, current_user.org_id, db)

    stmt = (
        select(AgentMCPServer)
        .where(
            and_(
                AgentMCPServer.agent_id == agent_id,
                AgentMCPServer.org_id == current_user.org_id,
            )
        )
        .order_by(AgentMCPServer.created_at.desc())
    )
    result = await db.execute(stmt)
    servers = result.scalars().all()

    return [_serialize_mcp_server(s) for s in servers]


@router.get(
    "/agents/{agent_id}/mcp-servers/{server_id}",
    response_model=MCPServerResponse,
)
async def get_mcp_server(
    agent_id: UUID,
    server_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get MCP server details including discovered tools."""
    await _get_agent_or_404(agent_id, current_user.org_id, db)

    stmt = select(AgentMCPServer).where(
        and_(
            AgentMCPServer.id == server_id,
            AgentMCPServer.agent_id == agent_id,
            AgentMCPServer.org_id == current_user.org_id,
        )
    )
    result = await db.execute(stmt)
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found",
        )

    return _serialize_mcp_server(server)


@router.put(
    "/agents/{agent_id}/mcp-servers/{server_id}",
    response_model=MCPServerResponse,
)
async def update_mcp_server(
    agent_id: UUID,
    server_id: UUID,
    data: MCPServerUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update MCP server configuration."""
    await _get_agent_or_404(agent_id, current_user.org_id, db)

    stmt = select(AgentMCPServer).where(
        and_(
            AgentMCPServer.id == server_id,
            AgentMCPServer.agent_id == agent_id,
            AgentMCPServer.org_id == current_user.org_id,
        )
    )
    result = await db.execute(stmt)
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(server, field, value)

    # Clear cached tools when config changes (they'll be re-discovered)
    if "endpoint_config" in update_data or "transport_type" in update_data or "auth_config" in update_data:
        server.discovered_tools = None

    await db.commit()
    await db.refresh(server)

    return _serialize_mcp_server(server)


@router.delete(
    "/agents/{agent_id}/mcp-servers/{server_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_mcp_server(
    agent_id: UUID,
    server_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove an MCP server from an agent."""
    await _get_agent_or_404(agent_id, current_user.org_id, db)

    stmt = select(AgentMCPServer).where(
        and_(
            AgentMCPServer.id == server_id,
            AgentMCPServer.agent_id == agent_id,
            AgentMCPServer.org_id == current_user.org_id,
        )
    )
    result = await db.execute(stmt)
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found",
        )

    await db.delete(server)
    await db.commit()


# ─── Test Connection ───


@router.post(
    "/agents/{agent_id}/mcp-servers/{server_id}/test",
    response_model=MCPServerTestResponse,
)
async def test_mcp_server(
    agent_id: UUID,
    server_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test MCP server connection and discover tools."""
    await _get_agent_or_404(agent_id, current_user.org_id, db)

    stmt = select(AgentMCPServer).where(
        and_(
            AgentMCPServer.id == server_id,
            AgentMCPServer.agent_id == agent_id,
            AgentMCPServer.org_id == current_user.org_id,
        )
    )
    result = await db.execute(stmt)
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found",
        )

    start_time = time.monotonic()

    try:
        client = create_mcp_client(
            server_name=server.name,
            server_id=str(server.id),
            transport_type=server.transport_type,
            endpoint_config=server.endpoint_config,
            auth_config=server.auth_config,
        )

        await client.connect()
        tools = await client.list_tools()
        await client.disconnect()

        latency_ms = int((time.monotonic() - start_time) * 1000)

        # Update cached tools in DB
        from datetime import datetime, timezone
        server.discovered_tools = [t.to_dict() for t in tools]
        server.last_connected_at = datetime.now(timezone.utc)
        await db.commit()

        return MCPServerTestResponse(
            status="connected",
            tools_discovered=len(tools),
            tools=[t.to_dict() for t in tools],
            latency_ms=latency_ms,
        )

    except MCPConnectionError as e:
        latency_ms = int((time.monotonic() - start_time) * 1000)
        return MCPServerTestResponse(
            status="error",
            error=str(e),
            latency_ms=latency_ms,
        )
    except Exception as e:
        latency_ms = int((time.monotonic() - start_time) * 1000)
        return MCPServerTestResponse(
            status="error",
            error=f"Unexpected error: {str(e)}",
            latency_ms=latency_ms,
        )


# ─── Templates ───


@router.get("/mcp-templates", response_model=List[MCPTemplateResponse])
async def list_mcp_templates(
    current_user: User = Depends(get_current_user),
):
    """List available pre-built MCP server templates."""
    templates = get_mcp_templates()
    return [
        MCPTemplateResponse(id=tid, **tdata)
        for tid, tdata in templates.items()
    ]
