"""API Gateway management commands."""

from __future__ import annotations

import json as _json
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt

from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.display import (
    get_output_format,
    print_dict_as_table,
    print_error,
    print_info,
    print_success,
    print_table,
    print_warning,
)

console = Console()
app = typer.Typer(help="🌐 API Gateway management")

# Note: gateway routes are at /api/gateway/* (no extra prefix from the router)
_GW = "/gateway"


# ── status ──────────────────────────────────────────────────────


@app.command("status")
def gateway_status(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Show gateway configuration and health."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching gateway status…[/cyan]"):
            config = api.get(f"{_GW}/config")

        if fmt == "json":
            console.print_json(_json.dumps(config, default=str))
        else:
            info = {
                "Endpoint": config.get("endpoint", config.get("base_url", "—")),
                "Default Model": config.get("default_model", "—"),
                "Rate Limit": f"{config.get('rate_limit', '—')} req/min",
                "Streaming": "✓" if config.get("enable_streaming", True) else "✗",
                "Logging": "✓" if config.get("enable_logging", True) else "✗",
            }
            print_dict_as_table(info, title="🌐 Gateway Configuration")
    except APIError as exc:
        print_error(f"Failed to get gateway status: {exc}")


# ── keys (sub-group) ───────────────────────────────────────────

keys_app = typer.Typer(help="Gateway API key management", no_args_is_help=True)


@keys_app.command("list")
def list_keys(
    json_output: bool = typer.Option(False, "--json"),
):
    """List all gateway API keys."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching keys…[/cyan]"):
            keys = api.get(f"{_GW}/keys")

        if fmt == "json":
            console.print_json(_json.dumps(keys, default=str))
        else:
            if not keys:
                print_info("No gateway keys. Create one: [cyan]bonito gateway keys create[/cyan]")
                return

            rows = []
            for k in keys:
                rows.append({
                    "Name": k.get("name", "Unnamed"),
                    "Key Prefix": k.get("key_prefix", k.get("key", "")[:12]) + "…",
                    "Created": k.get("created_at", "—"),
                })
            print_table(rows, title="🔑 Gateway API Keys")
            print_info(f"{len(keys)} key(s)")
    except APIError as exc:
        print_error(f"Failed to list keys: {exc}")


@keys_app.command("create")
def create_key(
    name: Optional[str] = typer.Option(None, "--name", help="Key name"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Create a new gateway API key."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    if not name:
        name = Prompt.ask("Key name", default="CLI Key")

    try:
        with console.status("[cyan]Creating key…[/cyan]"):
            result = api.post(f"{_GW}/keys", {"name": name})

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            key_value = result.get("key", result.get("raw_key", ""))
            print_success(f"Gateway key '{name}' created")
            console.print(f"\n[bold yellow]⚠  Save this key — it won't be shown again:[/bold yellow]")
            console.print(f"[bold green]{key_value}[/bold green]\n")
            console.print("[dim]Use this key with: Authorization: Bearer <key>[/dim]")
    except APIError as exc:
        print_error(f"Failed to create key: {exc}")


@keys_app.command("revoke")
def revoke_key(
    key_id: str = typer.Argument(..., help="Key UUID to revoke"),
    force: bool = typer.Option(False, "--force", "-f"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Revoke (delete) a gateway API key."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    if not force and fmt != "json":
        if not typer.confirm(f"Revoke key {key_id[:8]}…?"):
            print_info("Cancelled")
            return

    try:
        api.delete(f"{_GW}/keys/{key_id}")
        if fmt == "json":
            console.print_json(f'{{"status":"revoked","id":"{key_id}"}}')
        else:
            print_success(f"Key {key_id[:8]}… revoked")
            print_warning("Applications using this key will lose access")
    except APIError as exc:
        print_error(f"Failed to revoke key: {exc}")


app.add_typer(keys_app, name="keys")


# ── logs ────────────────────────────────────────────────────────


@app.command("logs")
def gateway_logs(
    limit: int = typer.Option(25, "--limit", "-n", help="Number of entries"),
    model: Optional[str] = typer.Option(None, "--model", help="Filter by model"),
    json_output: bool = typer.Option(False, "--json"),
):
    """View recent gateway request logs."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    params: dict = {"limit": limit}
    if model:
        params["model"] = model

    try:
        with console.status("[cyan]Fetching logs…[/cyan]"):
            logs = api.get(f"{_GW}/logs", params=params)

        if fmt == "json":
            console.print_json(_json.dumps(logs, default=str))
        else:
            if not logs:
                print_info("No recent gateway logs")
                return

            rows = []
            for entry in logs:
                status = entry.get("status", "success")
                color = "green" if status == "success" else "red"
                # Use model_used when available, fall back to model_requested
                model = entry.get("model_used") or entry.get("model_requested", "—")
                # Compute total tokens from input + output
                total_tokens = entry.get("input_tokens", 0) + entry.get("output_tokens", 0)
                rows.append({
                    "Time": entry.get("created_at", "—"),
                    "Model": model,
                    "Provider": entry.get("provider", "—"),
                    "Status": f"[{color}]{status}[/{color}]",
                    "Latency": f"{entry.get('latency_ms', 0):.0f}ms",
                    "Tokens": f"{total_tokens:,}",
                    "Cost": f"${entry.get('cost', 0):.4f}",
                })
            print_table(rows, title=f"📋 Gateway Logs (last {limit})")
    except APIError as exc:
        print_error(f"Failed to fetch logs: {exc}")


# ── usage ───────────────────────────────────────────────────────


@app.command("usage")
def gateway_usage(
    days: int = typer.Option(7, "--days", help="Days to show"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Show gateway usage statistics."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching usage…[/cyan]"):
            usage = api.get(f"{_GW}/usage", params={"days": days})

        if fmt == "json":
            console.print_json(_json.dumps(usage, default=str))
        else:
            info = {
                "Period": f"Last {days} days",
                "Total Requests": f"{usage.get('total_requests', 0):,}",
                "Total Tokens": f"{usage.get('total_tokens', 0):,}",
                "Total Cost": f"${usage.get('total_cost', 0):.2f}",
                "Active Keys": usage.get("unique_keys", usage.get("active_keys", "—")),
            }
            print_dict_as_table(info, title="📊 Gateway Usage")

            # Top models if present
            top = usage.get("top_models", usage.get("by_model", []))
            if top and isinstance(top, list):
                rows = [
                    {
                        "Model": m.get("model", m.get("model_id", "—")),
                        "Requests": f"{m.get('requests', m.get('count', 0)):,}",
                    }
                    for m in top[:5]
                ]
                print_table(rows, title="Top Models")
    except APIError as exc:
        print_error(f"Failed to get usage: {exc}")


# ── config (sub-group) ─────────────────────────────────────────

config_app = typer.Typer(help="Gateway configuration", no_args_is_help=True)


@config_app.command("show")
def show_config(json_output: bool = typer.Option(False, "--json")):
    """Show current gateway configuration."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching config…[/cyan]"):
            config = api.get(f"{_GW}/config")

        if fmt == "json":
            console.print_json(_json.dumps(config, default=str))
        else:
            display = {}
            for k, v in config.items():
                label = k.replace("_", " ").title()
                if isinstance(v, bool):
                    display[label] = "✓" if v else "✗"
                elif isinstance(v, list):
                    display[label] = ", ".join(str(i) for i in v)
                else:
                    display[label] = str(v)
            print_dict_as_table(display, title="⚙️  Gateway Configuration")
    except APIError as exc:
        print_error(f"Failed to get config: {exc}")


@config_app.command("set")
def set_config(
    field: str = typer.Argument(..., help="Configuration field"),
    value: str = typer.Argument(..., help="New value"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Update a gateway configuration value."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    # Coerce types
    coerced: object = value
    if field in ("rate_limit", "timeout_seconds", "max_tokens", "cache_ttl"):
        coerced = int(value)
    elif field in ("enable_streaming", "enable_logging"):
        coerced = value.lower() in ("true", "yes", "1", "on")

    try:
        with console.status("[cyan]Updating config…[/cyan]"):
            current = api.get(f"{_GW}/config")
            current[field] = coerced
            updated = api.put(f"{_GW}/config", current)

        if fmt == "json":
            console.print_json(_json.dumps(updated, default=str))
        else:
            print_success(f"{field} = {coerced}")
    except APIError as exc:
        print_error(f"Failed to update config: {exc}")


app.add_typer(config_app, name="config")
