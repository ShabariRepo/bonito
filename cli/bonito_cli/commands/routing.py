"""Routing rule management commands."""

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
)

console = Console()
app = typer.Typer(help="Routing rule management")


# -- list --------------------------------------------------------------


@app.command("list")
def list_rules(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all routing rules."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching routing rules...[/cyan]"):
            rules = api.get("/routing/rules")

        if fmt == "json":
            console.print_json(_json.dumps(rules, default=str))
        else:
            if rules:
                data = [
                    {
                        "ID": str(r.get("id", ""))[:8] + "...",
                        "Name": r.get("name", ""),
                        "Strategy": r.get("strategy", ""),
                        "Priority": str(r.get("priority", "")),
                        "Enabled": "Yes" if r.get("enabled") else "No",
                    }
                    for r in rules
                ]
                print_table(data, title="Routing Rules")
                print_info(f"{len(rules)} rule(s)")
            else:
                print_info("No routing rules configured.")
    except APIError as exc:
        print_error(f"Failed to list routing rules: {exc}")


# -- create ------------------------------------------------------------


@app.command("create")
def create_rule(
    name: str = typer.Option(..., "--name", "-n", help="Rule name"),
    strategy: str = typer.Option(..., "--strategy", "-s", help="Routing strategy (cost/latency/balanced/failover/ab_test)"),
    priority: int = typer.Option(0, "--priority", "-p", help="Priority (lower = higher priority)"),
    conditions: Optional[str] = typer.Option(None, "--conditions", "-c", help="Conditions JSON"),
    enabled: bool = typer.Option(True, "--enabled/--disabled", help="Enable the rule"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Create a new routing rule."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    body = {
        "name": name,
        "strategy": strategy,
        "priority": priority,
        "enabled": enabled,
    }

    if conditions:
        try:
            body["conditions_json"] = _json.loads(conditions)
        except _json.JSONDecodeError:
            print_error("Invalid JSON for --conditions")
            return

    try:
        with console.status("[cyan]Creating routing rule...[/cyan]"):
            result = api.post("/routing/rules", body)

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            print_success(f"Routing rule '{name}' created (ID: {result.get('id', 'N/A')})")
    except APIError as exc:
        print_error(f"Failed to create routing rule: {exc}")


# -- update ------------------------------------------------------------


@app.command("update")
def update_rule(
    rule_id: str = typer.Argument(..., help="Routing rule ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Update name"),
    strategy: Optional[str] = typer.Option(None, "--strategy", "-s", help="Update strategy"),
    priority: Optional[int] = typer.Option(None, "--priority", "-p", help="Update priority"),
    conditions: Optional[str] = typer.Option(None, "--conditions", "-c", help="Update conditions JSON"),
    enabled: Optional[bool] = typer.Option(None, "--enabled/--disabled", help="Enable or disable"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Update a routing rule."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    body = {}
    if name is not None:
        body["name"] = name
    if strategy is not None:
        body["strategy"] = strategy
    if priority is not None:
        body["priority"] = priority
    if enabled is not None:
        body["enabled"] = enabled
    if conditions is not None:
        try:
            body["conditions_json"] = _json.loads(conditions)
        except _json.JSONDecodeError:
            print_error("Invalid JSON for --conditions")
            return

    if not body:
        print_error("No updates specified")
        return

    try:
        with console.status("[cyan]Updating routing rule...[/cyan]"):
            result = api.patch(f"/routing/rules/{rule_id}", body)

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            print_success("Routing rule updated successfully")
    except APIError as exc:
        print_error(f"Failed to update routing rule: {exc}")


# -- delete ------------------------------------------------------------


@app.command("delete")
def delete_rule(
    rule_id: str = typer.Argument(..., help="Routing rule ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a routing rule."""
    ensure_authenticated()

    if not yes:
        confirmed = Confirm.ask(f"[yellow]Delete routing rule '{rule_id}'?[/yellow]")
        if not confirmed:
            print_info("Cancelled")
            raise typer.Exit(0)

    try:
        with console.status("[cyan]Deleting routing rule...[/cyan]"):
            api.delete(f"/routing/rules/{rule_id}")

        print_success("Routing rule deleted successfully")
    except APIError as exc:
        print_error(f"Failed to delete routing rule: {exc}")
