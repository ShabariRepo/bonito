"""AI model management commands."""

from __future__ import annotations

import json as _json
from typing import List, Optional

import typer
from rich.console import Console

from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.display import (
    format_cost,
    format_tokens,
    get_output_format,
    print_dict_as_table,
    print_error,
    print_info,
    print_model_table,
    print_success,
    print_table,
    print_warning,
)

console = Console()
app = typer.Typer(help="🤖 AI model catalogue")


# ── list ────────────────────────────────────────────────────────


@app.command("list")
def list_models(
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Filter by provider type"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search by name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    List available AI models.

    Examples:
        bonito models list
        bonito models list --provider aws_bedrock
        bonito models list --search claude
    """
    fmt = get_output_format(json_output)
    ensure_authenticated()

    params: dict = {}
    if provider:
        params["provider"] = provider
    if search:
        params["search"] = search

    try:
        with console.status("[cyan]Fetching models…[/cyan]"):
            models = api.get("/models/", params=params if params else None)

        if fmt == "json":
            console.print_json(_json.dumps(models, default=str))
        else:
            print_model_table(models, fmt)
            total = len(models) if isinstance(models, list) else 0
            console.print(f"\n[dim]{total} model(s) found[/dim]")
    except APIError as exc:
        print_error(f"Failed to list models: {exc}")


# ── search ──────────────────────────────────────────────────────


@app.command("search")
def search_models(
    query: str = typer.Argument(..., help="Search query"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Search models by name or description."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    params: dict = {"search": query}
    if provider:
        params["provider"] = provider

    try:
        with console.status(f"[cyan]Searching '{query}'…[/cyan]"):
            models = api.get("/models/", params=params)

        if fmt == "json":
            console.print_json(_json.dumps(models, default=str))
        else:
            if not models:
                print_info(f"No models match '{query}'")
                return
            print_model_table(models, fmt)
            console.print(f"\n[dim]{len(models)} result(s) for '{query}'[/dim]")
    except APIError as exc:
        print_error(f"Search failed: {exc}")


# ── info ────────────────────────────────────────────────────────


@app.command("info")
def model_info(
    model_id: str = typer.Argument(..., help="Model UUID"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Show detailed information about a model."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching model details…[/cyan]"):
            info = api.get(f"/models/{model_id}")
            # Also try to get extended details
            details = {}
            try:
                details = api.get(f"/models/{model_id}/details")
            except APIError:
                pass

        combined = {**info, **details}

        if fmt == "json":
            console.print_json(_json.dumps(combined, default=str))
        else:
            basic = {
                "Name": combined.get("display_name", combined.get("model_id", "—")),
                "Provider": combined.get("provider_type", "—"),
                "Model ID": combined.get("model_id", "—"),
                "Status": "✓ Enabled" if combined.get("is_enabled", combined.get("enabled", True)) else "Locked",
            }
            print_dict_as_table(basic, title=f"🤖 {combined.get('display_name', model_id)}")

            caps = combined.get("capabilities", {})
            if caps:
                cap_info = {
                    "Max Input Tokens": format_tokens(caps.get("max_input_tokens", 0)),
                    "Max Output Tokens": format_tokens(caps.get("max_output_tokens", 0)),
                    "Streaming": "✓" if caps.get("supports_streaming") else "✗",
                    "Function Calling": "✓" if caps.get("supports_function_calling") else "✗",
                    "Vision": "✓" if caps.get("supports_vision") else "✗",
                }
                print_dict_as_table(cap_info, title="Capabilities")
    except APIError as exc:
        print_error(f"Failed to get model info: {exc}")


# ── enable / activate ───────────────────────────────────────────


@app.command("enable")
def enable_model(
    model_ids: List[str] = typer.Argument(..., help="Model UUID(s) to enable"),
    json_output: bool = typer.Option(False, "--json"),
):
    """
    Enable (activate) one or more AI models.

    Examples:
        bonito models enable <model-uuid>
        bonito models enable <id1> <id2> <id3>
    """
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        if len(model_ids) == 1:
            with console.status("[cyan]Activating model…[/cyan]"):
                result = api.post(f"/models/{model_ids[0]}/activate")
            if fmt == "json":
                console.print_json(_json.dumps(result, default=str))
            else:
                print_success(f"Model {model_ids[0][:8]}… activated")
        else:
            with console.status(f"[cyan]Activating {len(model_ids)} models…[/cyan]"):
                result = api.post("/models/activate-bulk", {"model_ids": model_ids})
            if fmt == "json":
                console.print_json(_json.dumps(result, default=str))
            else:
                ok = result.get("successful", [])
                fail = result.get("failed", [])
                if ok:
                    print_success(f"{len(ok)} model(s) activated")
                if fail:
                    print_warning(f"{len(fail)} model(s) failed")
                    for f_item in fail:
                        console.print(f"  [red]✗[/red] {f_item.get('model_id', '?')}: {f_item.get('error', '?')}")
    except APIError as exc:
        print_error(f"Activation failed: {exc}")


# ── sync ────────────────────────────────────────────────────────


@app.command("sync")
def sync_models(
    provider: Optional[str] = typer.Option(None, "--provider", help="Sync for a specific provider UUID"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Sync the model catalogue from connected cloud providers."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        endpoint = f"/models/sync/{provider}" if provider else "/models/sync"
        with console.status("[cyan]Syncing models…[/cyan]"):
            result = api.post(endpoint)

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            print_success("Model sync complete")
            added = result.get("added", result.get("models_added", 0))
            console.print(f"  ➕ Added: {added}")
            if result.get("errors"):
                for err in result["errors"]:
                    console.print(f"  [red]✗[/red] {err}")
    except APIError as exc:
        print_error(f"Sync failed: {exc}")
