"""Agent memory management commands."""

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
app = typer.Typer(help="Agent persistent memory management")


# -- list --------------------------------------------------------------


@app.command("list")
def list_memories(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    memory_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by memory type"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max results"),
    order_by: str = typer.Option("created_at", "--order", help="Order by: created_at, importance, accessed, updated"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List memories for an agent."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    params = {"limit": limit, "order_by": order_by}
    if memory_type:
        params["memory_type"] = memory_type

    try:
        with console.status("[cyan]Fetching memories...[/cyan]"):
            memories = api.get(f"/agents/{agent_id}/memories", params=params)

        if fmt == "json":
            console.print_json(_json.dumps(memories, default=str))
        else:
            if memories:
                data = [
                    {
                        "ID": str(m.get("id", ""))[:8] + "...",
                        "Type": m.get("memory_type", ""),
                        "Content": (m.get("content", "") or "")[:50],
                        "Importance": str(m.get("importance_score", "")),
                        "Created": format_timestamp(m.get("created_at")),
                    }
                    for m in memories
                ]
                print_table(data, title="Agent Memories")
                print_info(f"{len(memories)} memory(ies)")
            else:
                print_info("No memories found for this agent.")
    except APIError as exc:
        print_error(f"Failed to list memories: {exc}")


# -- search ------------------------------------------------------------


@app.command("search")
def search_memories(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max results"),
    min_importance: Optional[float] = typer.Option(None, "--min-importance", help="Minimum importance score"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Search agent memories using vector similarity."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    body = {"query": query, "limit": limit}
    if min_importance is not None:
        body["min_importance"] = min_importance

    try:
        with console.status("[cyan]Searching memories...[/cyan]"):
            result = api.post(f"/agents/{agent_id}/memories/search", body)

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            memories = result.get("memories", [])
            total = result.get("total_found", 0)
            if memories:
                data = [
                    {
                        "ID": str(m.get("id", ""))[:8] + "...",
                        "Type": m.get("memory_type", ""),
                        "Content": (m.get("content", "") or "")[:60],
                        "Importance": str(m.get("importance_score", "")),
                    }
                    for m in memories
                ]
                print_table(data, title=f"Search Results for '{query}'")
                print_info(f"{total} result(s) found")
            else:
                print_info("No matching memories found.")
    except APIError as exc:
        print_error(f"Failed to search memories: {exc}")


# -- delete ------------------------------------------------------------


@app.command("delete")
def delete_memory(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    memory_id: str = typer.Argument(..., help="Memory ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete an agent memory."""
    ensure_authenticated()

    if not yes:
        confirmed = Confirm.ask(f"[yellow]Delete memory '{memory_id}'?[/yellow]")
        if not confirmed:
            print_info("Cancelled")
            raise typer.Exit(0)

    try:
        with console.status("[cyan]Deleting memory...[/cyan]"):
            api.delete(f"/agents/{agent_id}/memories/{memory_id}")

        print_success("Memory deleted successfully")
    except APIError as exc:
        print_error(f"Failed to delete memory: {exc}")


# -- stats -------------------------------------------------------------


@app.command("stats")
def memory_stats(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Get agent memory statistics."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching memory stats...[/cyan]"):
            stats = api.get(f"/agents/{agent_id}/memories/stats")

        if fmt == "json":
            console.print_json(_json.dumps(stats, default=str))
        else:
            if isinstance(stats, dict):
                print_dict_as_table(stats, title="Memory Statistics")
            else:
                console.print(stats)
    except APIError as exc:
        print_error(f"Failed to get memory stats: {exc}")
