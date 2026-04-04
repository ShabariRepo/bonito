"""Org secrets management commands."""

from __future__ import annotations

from typing import Optional
from pathlib import Path

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
    print_warning,
)

console = Console()
app = typer.Typer(help="🔐 Org secrets management")


# ── list ────────────────────────────────────────────────────────


@app.command("list")
def list_secrets(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all org secrets (metadata only, no values)."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching secrets…[/cyan]"):
            secrets = api.get("/secrets")

        if fmt == "json":
            import json as _json
            console.print_json(_json.dumps(secrets, default=str))
        else:
            if secrets:
                headers = ["Name", "Description", "Created", "Updated"]
                rows = [
                    [
                        s.get("name", "—"),
                        s.get("description", "")[:50] or "—",
                        s.get("created_at", "—")[:10] if s.get("created_at") else "—",
                        s.get("updated_at", "—")[:10] if s.get("updated_at") else "—",
                    ]
                    for s in secrets
                ]
                print_table(headers, rows, title="🔐 Org Secrets")
                print_info(f"{len(secrets)} secret(s)")
            else:
                print_info("No secrets configured — add one with [cyan]bonito secrets set <name> <value>[/cyan]")
    except APIError as exc:
        print_error(f"Failed to list secrets: {exc}")


# ── get ────────────────────────────────────────────────────────


@app.command("get")
def get_secret(
    name: str = typer.Argument(..., help="Secret name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Get a secret value."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status(f"[cyan]Retrieving secret '{name}'…[/cyan]"):
            secret = api.get(f"/secrets/{name}")

        if fmt == "json":
            import json as _json
            console.print_json(_json.dumps(secret, default=str))
        else:
            # Print just the value for easy piping
            console.print(secret.get("value", ""))
    except APIError as exc:
        print_error(f"Failed to get secret: {exc}")


# ── set ────────────────────────────────────────────────────────


@app.command("set")
def set_secret(
    name: str = typer.Argument(..., help="Secret name"),
    value: str = typer.Argument(..., help="Secret value or @filepath to read from file"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Secret description"),
):
    """Create or update a secret."""
    ensure_authenticated()

    # Handle @filepath syntax
    actual_value = value
    if value.startswith("@"):
        filepath = Path(value[1:])
        if not filepath.exists():
            print_error(f"File not found: {filepath}")
            raise typer.Exit(1)
        try:
            actual_value = filepath.read_text().strip()
        except Exception as e:
            print_error(f"Failed to read file: {e}")
            raise typer.Exit(1)

    try:
        # Check if secret exists
        try:
            api.get(f"/secrets/{name}")
            is_update = True
        except APIError:
            is_update = False

        with console.status(f"[cyan]{'Updating' if is_update else 'Creating'} secret '{name}'…[/cyan]"):
            if is_update:
                body = {"value": actual_value}
                if description is not None:
                    body["description"] = description
                api.put(f"/secrets/{name}", json=body)
            else:
                body = {"name": name, "value": actual_value}
                if description:
                    body["description"] = description
                api.post("/secrets", json=body)

        print_success(f"Secret '{name}' {'updated' if is_update else 'created'} successfully")
    except APIError as exc:
        print_error(f"Failed to set secret: {exc}")


# ── delete ────────────────────────────────────────────────────────


@app.command("delete")
def delete_secret(
    name: str = typer.Argument(..., help="Secret name"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a secret."""
    ensure_authenticated()

    if not yes:
        confirmed = Confirm.ask(f"[yellow]Are you sure you want to delete secret '{name}'?[/yellow]")
        if not confirmed:
            print_info("Cancelled")
            raise typer.Exit(0)

    try:
        with console.status(f"[cyan]Deleting secret '{name}'…[/cyan]"):
            api.delete(f"/secrets/{name}")

        print_success(f"Secret '{name}' deleted successfully")
    except APIError as exc:
        print_error(f"Failed to delete secret: {exc}")
