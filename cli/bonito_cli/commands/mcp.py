"""MCP server management commands."""

from __future__ import annotations

import json as _json
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Confirm

from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.display import (
    get_output_format,
    print_error,
    print_info,
    print_success,
    print_table,
    print_dict_as_table,
    format_timestamp,
)

console = Console()
app = typer.Typer(help="MCP (Model Context Protocol) server management")


# -- list --------------------------------------------------------------


@app.command("list")
def list_servers(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List MCP servers configured for an agent."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching MCP servers...[/cyan]"):
            servers = api.get(f"/agents/{agent_id}/mcp-servers")

        if fmt == "json":
            console.print_json(_json.dumps(servers, default=str))
        else:
            if servers:
                data = [
                    {
                        "ID": str(s.get("id", ""))[:8] + "...",
                        "Name": s.get("name", ""),
                        "Transport": s.get("transport_type", ""),
                        "Enabled": "Yes" if s.get("enabled") else "No",
                        "Tools": str(len(s.get("discovered_tools", []) or [])),
                        "Last Connected": format_timestamp(s.get("last_connected_at")),
                    }
                    for s in servers
                ]
                print_table(data, title="MCP Servers")
                print_info(f"{len(servers)} server(s)")
            else:
                print_info("No MCP servers configured for this agent.")
    except APIError as exc:
        print_error(f"Failed to list MCP servers: {exc}")


# -- create ------------------------------------------------------------


@app.command("create")
def create_server(
    agent_id: str = typer.Option(..., "--agent", "-a", help="Agent ID"),
    name: str = typer.Option(..., "--name", "-n", help="Server name"),
    transport: str = typer.Option(..., "--transport", "-t", help="Transport type: stdio or http"),
    url: Optional[str] = typer.Option(None, "--url", help="HTTP endpoint URL (for http transport)"),
    command: Optional[str] = typer.Option(None, "--command", help="Command to execute (for stdio transport)"),
    template_id: Optional[str] = typer.Option(None, "--template", help="Use a pre-built template"),
    enabled: bool = typer.Option(True, "--enabled/--disabled", help="Enable the server"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Register an MCP server for an agent."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    body = {
        "name": name,
        "transport_type": transport,
        "enabled": enabled,
    }

    endpoint_config = {}
    if transport == "http" and url:
        endpoint_config["url"] = url
    elif transport == "stdio" and command:
        endpoint_config["command"] = command

    if endpoint_config:
        body["endpoint_config"] = endpoint_config

    if template_id:
        body["template_id"] = template_id

    try:
        with console.status("[cyan]Creating MCP server...[/cyan]"):
            result = api.post(f"/agents/{agent_id}/mcp-servers", body)

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            print_success(f"MCP server '{name}' created (ID: {result.get('id', 'N/A')})")
    except APIError as exc:
        print_error(f"Failed to create MCP server: {exc}")


# -- update ------------------------------------------------------------


@app.command("update")
def update_server(
    agent_id: str = typer.Option(..., "--agent", "-a", help="Agent ID"),
    server_id: str = typer.Argument(..., help="MCP server ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Update name"),
    url: Optional[str] = typer.Option(None, "--url", help="Update HTTP URL"),
    command: Optional[str] = typer.Option(None, "--command", help="Update stdio command"),
    enabled: Optional[bool] = typer.Option(None, "--enabled/--disabled", help="Enable or disable"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Update MCP server configuration."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    body = {}
    if name is not None:
        body["name"] = name
    if enabled is not None:
        body["enabled"] = enabled
    if url is not None:
        body["endpoint_config"] = {"url": url}
    elif command is not None:
        body["endpoint_config"] = {"command": command}

    if not body:
        print_error("No updates specified")
        return

    try:
        with console.status("[cyan]Updating MCP server...[/cyan]"):
            result = api.put(f"/agents/{agent_id}/mcp-servers/{server_id}", body)

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            print_success("MCP server updated successfully")
    except APIError as exc:
        print_error(f"Failed to update MCP server: {exc}")


# -- delete ------------------------------------------------------------


@app.command("delete")
def delete_server(
    agent_id: str = typer.Option(..., "--agent", "-a", help="Agent ID"),
    server_id: str = typer.Argument(..., help="MCP server ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Remove an MCP server from an agent."""
    ensure_authenticated()

    if not yes:
        confirmed = Confirm.ask(f"[yellow]Delete MCP server '{server_id}'?[/yellow]")
        if not confirmed:
            print_info("Cancelled")
            raise typer.Exit(0)

    try:
        with console.status("[cyan]Deleting MCP server...[/cyan]"):
            api.delete(f"/agents/{agent_id}/mcp-servers/{server_id}")

        print_success("MCP server deleted successfully")
    except APIError as exc:
        print_error(f"Failed to delete MCP server: {exc}")


# -- test --------------------------------------------------------------


@app.command("test")
def test_server(
    agent_id: str = typer.Option(..., "--agent", "-a", help="Agent ID"),
    server_id: str = typer.Argument(..., help="MCP server ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Test MCP server connection and discover tools."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Testing MCP server connection...[/cyan]"):
            result = api.post(f"/agents/{agent_id}/mcp-servers/{server_id}/test")

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            status = result.get("status", "unknown")
            if status == "connected":
                print_success(f"Connection successful - {result.get('tools_discovered', 0)} tool(s) discovered ({result.get('latency_ms', 0)}ms)")
                tools = result.get("tools", [])
                if tools:
                    data = [
                        {
                            "Name": t.get("name", ""),
                            "Description": (t.get("description", "") or "")[:50],
                        }
                        for t in tools
                    ]
                    print_table(data, title="Discovered Tools")
            else:
                print_error(f"Connection failed: {result.get('error', 'Unknown error')}")
    except APIError as exc:
        print_error(f"Failed to test MCP server: {exc}")
