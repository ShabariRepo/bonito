"""Audit log commands."""

from __future__ import annotations

import json as _json
from typing import Optional

import typer
from rich.console import Console

from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.display import (
    get_output_format,
    print_error,
    print_info,
    print_table,
    format_timestamp,
)

console = Console()
app = typer.Typer(help="Audit log viewer")


@app.command("list")
def list_logs(
    action: Optional[str] = typer.Option(None, "--action", "-a", help="Filter by action (e.g. create, update, delete)"),
    resource_type: Optional[str] = typer.Option(None, "--resource", "-r", help="Filter by resource type"),
    user_name: Optional[str] = typer.Option(None, "--user", "-u", help="Filter by user name"),
    date_from: Optional[str] = typer.Option(None, "--from", help="Filter from date (ISO format: 2026-01-01)"),
    date_to: Optional[str] = typer.Option(None, "--to", help="Filter to date (ISO format: 2026-12-31)"),
    page: int = typer.Option(1, "--page", help="Page number"),
    page_size: int = typer.Option(20, "--page-size", help="Page size (max 100)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List audit logs with optional filters."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    params = {"page": page, "page_size": page_size}
    if action:
        params["action"] = action
    if resource_type:
        params["resource_type"] = resource_type
    if user_name:
        params["user_name"] = user_name
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to

    try:
        with console.status("[cyan]Fetching audit logs...[/cyan]"):
            result = api.get("/audit", params=params)

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            items = result.get("items", [])
            total = result.get("total", 0)

            if items:
                data = [
                    {
                        "Timestamp": format_timestamp(i.get("created_at")),
                        "User": i.get("user_name", ""),
                        "Action": i.get("action", ""),
                        "Resource": i.get("resource_type", ""),
                        "Resource ID": str(i.get("resource_id", ""))[:8] + "..." if i.get("resource_id") else "",
                        "Details": (str(i.get("details", "")) or "")[:40],
                    }
                    for i in items
                ]
                print_table(data, title="Audit Logs")
                print_info(f"Page {page} - Showing {len(items)} of {total} total entries")
            else:
                print_info("No audit log entries found.")
    except APIError as exc:
        print_error(f"Failed to list audit logs: {exc}")
