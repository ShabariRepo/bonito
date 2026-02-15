"""Deployment management commands."""

from __future__ import annotations

import json as _json
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..api import api, APIError
from ..config import is_authenticated
from ..utils.auth import ensure_authenticated
from ..utils.display import (
    format_status,
    get_output_format,
    print_error,
    print_info,
    print_success,
)

console = Console()
app = typer.Typer(help="🚀 Deployment management")

_EMOJI = {"aws": "☁️ ", "azure": "🔷", "gcp": "🔺"}


# ── list ────────────────────────────────────────────────────────


@app.command("list")
def list_deployments(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all deployments."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching deployments…[/cyan]"):
            deployments = api.get("/deployments/")

        if fmt == "json":
            console.print_json(_json.dumps(deployments, default=str))
            return

        if not deployments:
            console.print(
                Panel(
                    "[dim]No deployments yet.[/dim]\n\nCreate one: [cyan]bonito deployments create[/cyan]",
                    title="🚀 Deployments",
                    border_style="dim",
                )
            )
            return

        table = Table(title="🚀 Deployments", border_style="dim")
        table.add_column("Name", style="bold")
        table.add_column("Model")
        table.add_column("Provider")
        table.add_column("Status")
        table.add_column("Cost")

        for d in deployments:
            cfg = d.get("config", {})
            ptype = cfg.get("provider_type", "")
            emoji = _EMOJI.get(ptype, "☁️ ")
            est = cfg.get("cost_estimate", {})
            cost = f"${est['monthly']:.0f}/mo" if est.get("monthly", 0) > 0 else "Pay-per-use"
            status_style = "green" if d["status"] == "active" else "yellow" if d["status"] == "deploying" else "red"

            table.add_row(
                cfg.get("name", "—"),
                cfg.get("model_display_name", "—"),
                f"{emoji}{ptype.upper()}",
                f"[{status_style}]{d['status']}[/{status_style}]",
                cost,
            )

        console.print(table)
        console.print(f"\n[dim]{len(deployments)} deployment(s)[/dim]")

    except APIError as exc:
        print_error(f"Failed to list deployments: {exc}")


# ── create ──────────────────────────────────────────────────────


@app.command("create")
def create_deployment(
    model_id: Optional[str] = typer.Option(None, "--model", "-m", help="Model UUID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Deployment name"),
    model_units: int = typer.Option(0, "--units", help="AWS model units (0 = on-demand)"),
    tpm: int = typer.Option(10, "--tpm", help="Azure tokens per minute (thousands)"),
    tier: str = typer.Option("Standard", "--tier", help="Azure tier"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search model by name"),
    json_output: bool = typer.Option(False, "--json"),
):
    """
    Create a new model deployment.

    Examples:
        bonito deployments create --search "nova pro" --name prod-nova
        bonito deployments create --model <uuid> --name my-deploy
    """
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        # Resolve model by search
        if search and not model_id:
            with console.status(f"[cyan]Searching '{search}'…[/cyan]"):
                models = api.get("/models/")

            matches = [
                m
                for m in models
                if search.lower() in m.get("display_name", "").lower()
                or search.lower() in m.get("model_id", "").lower()
            ]

            if not matches:
                print_error(f"No models matching '{search}'")
                return

            if len(matches) == 1:
                model_id = matches[0]["id"]
                console.print(f"[green]Found:[/green] {matches[0]['display_name']}")
            else:
                table = Table(title=f"Models matching '{search}'", border_style="dim")
                table.add_column("#", style="bold cyan", width=3)
                table.add_column("Name")
                table.add_column("Provider")
                for i, m in enumerate(matches[:10], 1):
                    table.add_row(str(i), m.get("display_name", "—"), m.get("provider_type", "—").upper())
                console.print(table)
                idx = int(Prompt.ask("Select #", default="1")) - 1
                if 0 <= idx < len(matches):
                    model_id = matches[idx]["id"]
                else:
                    print_error("Invalid selection")
                    return

        if not model_id:
            print_error("Model ID required. Use --model <uuid> or --search <name>")
            return

        cfg: dict = {}
        if name:
            cfg["name"] = name
        cfg["model_units"] = model_units
        if tpm != 10:
            cfg["tpm"] = tpm
        if tier != "Standard":
            cfg["tier"] = tier

        with console.status("[cyan]Creating deployment…[/cyan]"):
            result = api.post("/deployments/", {"model_id": model_id, "config": cfg})

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            rc = result.get("config", {})
            console.print(
                Panel(
                    f"[green]✓ Deployment created[/green]\n\n"
                    f"  Name:     [bold]{rc.get('name', '—')}[/bold]\n"
                    f"  Model:    {rc.get('model_display_name', '—')}\n"
                    f"  Provider: {_EMOJI.get(rc.get('provider_type', ''), '☁️ ')}{rc.get('provider_type', '').upper()}\n"
                    f"  Status:   {result.get('status', '—')}\n"
                    f"\n  [dim]{rc.get('deploy_message', '')}[/dim]",
                    title="🚀 Deployment Created",
                    border_style="green",
                )
            )
    except APIError as exc:
        print_error(f"Deployment creation failed: {exc}")


# ── delete ──────────────────────────────────────────────────────


@app.command("delete")
def delete_deployment(
    deployment_id: str = typer.Argument(help="Deployment UUID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Delete a deployment."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    if not force and fmt != "json":
        if not Confirm.ask(f"[red]Delete deployment {deployment_id[:8]}…?[/red]"):
            console.print("[dim]Cancelled[/dim]")
            return

    try:
        with console.status("[cyan]Deleting deployment…[/cyan]"):
            api.delete(f"/deployments/{deployment_id}")
        if fmt == "json":
            console.print_json(f'{{"status":"deleted","id":"{deployment_id}"}}')
        else:
            print_success(f"Deployment {deployment_id[:8]}… deleted")
    except APIError as exc:
        print_error(f"Delete failed: {exc}")


# ── status ──────────────────────────────────────────────────────


@app.command("status")
def deployment_status(
    deployment_id: str = typer.Argument(help="Deployment UUID"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Refresh deployment status from the cloud provider."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Checking status…[/cyan]"):
            result = api.post(f"/deployments/{deployment_id}/status")

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            st = result.get("status", "unknown")
            color = "green" if st == "active" else "yellow" if st == "deploying" else "red"
            console.print(f"[{color}]Status: {st}[/{color}]")

            cloud = result.get("cloud_status", {})
            for k, v in cloud.items():
                console.print(f"  [dim]{k}:[/dim] {v}")
    except APIError as exc:
        print_error(f"Status check failed: {exc}")
