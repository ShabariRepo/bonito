"""Routing policy management commands."""

from __future__ import annotations

import json as _json
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt

from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.display import (
    format_cost,
    get_output_format,
    print_dict_as_table,
    print_error,
    print_info,
    print_success,
    print_table,
    print_warning,
)

console = Console()
app = typer.Typer(help="🎯 Routing policy management")

# Backend route prefix
_RP = "/policies"


# ── list ────────────────────────────────────────────────────────


@app.command("list")
def list_policies(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all routing policies."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching policies…[/cyan]"):
            policies = api.get(f"{_RP}/")

        if fmt == "json":
            console.print_json(_json.dumps(policies, default=str))
            return

        if not policies:
            print_info("No routing policies. Create one: [cyan]bonito policies create[/cyan]")
            return

        rows = []
        for p in policies:
            enabled = p.get("enabled", p.get("is_active", True))
            models = p.get("models", p.get("model_ids", []))
            # Models may be dicts (e.g. {"model_id": "…", "weight": 50}) — show a count
            if models and isinstance(models[0], dict):
                model_text = f"{len(models)} model{'s' if len(models) != 1 else ''}"
            else:
                model_text = ", ".join(str(m) for m in models)[:40]
                if len(model_text) >= 40:
                    model_text += "…"
            rows.append({
                "ID": str(p.get("id", ""))[:8] + "…",
                "Name": p.get("name", "—"),
                "Strategy": p.get("strategy", "—").replace("_", " ").title(),
                "Status": "[green]✓[/green]" if enabled else "[dim]off[/dim]",
                "Models": model_text or "—",
            })
        print_table(rows, title="🎯 Routing Policies")
        enabled_n = sum(1 for p in policies if p.get("enabled", p.get("is_active", True)))
        print_info(f"{len(policies)} total, {enabled_n} active")

    except APIError as exc:
        print_error(f"Failed to list policies: {exc}")


# ── create ──────────────────────────────────────────────────────

_STRATEGIES = ["cost_optimized", "latency_optimized", "quality_optimized", "round_robin"]


@app.command("create")
def create_policy(
    name: Optional[str] = typer.Option(None, "--name", help="Policy name"),
    strategy: Optional[str] = typer.Option(None, "--strategy", help="Routing strategy"),
    models: Optional[str] = typer.Option(None, "--models", help="Comma-separated model UUIDs"),
    json_output: bool = typer.Option(False, "--json"),
):
    """
    Create a new routing policy.

    Examples:
        bonito policies create --name "Cost Saver" --strategy cost_optimized --models id1,id2
        bonito policies create   # interactive
    """
    fmt = get_output_format(json_output)
    ensure_authenticated()

    if not name:
        name = Prompt.ask("Policy name")
    if not strategy:
        console.print("\n[bold]Strategies:[/bold]")
        for i, s in enumerate(_STRATEGIES, 1):
            console.print(f"  {i}. {s.replace('_', ' ').title()}")
        while True:
            try:
                c = int(Prompt.ask("Select (1-4)"))
                if 1 <= c <= len(_STRATEGIES):
                    strategy = _STRATEGIES[c - 1]
                    break
            except ValueError:
                pass
            console.print("[red]Invalid[/red]")
    if not models:
        models = Prompt.ask("Model UUIDs (comma-separated)")

    model_list = [m.strip() for m in models.split(",") if m.strip()]
    # Backend expects models as list of ModelConfiguration objects
    model_configs = [{"model_id": m, "weight": 50, "role": "primary"} for m in model_list]

    try:
        with console.status("[cyan]Creating policy…[/cyan]"):
            result = api.post(f"{_RP}/", {
                "name": name,
                "strategy": strategy,
                "models": model_configs,
            })

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            print_success(f"Policy '{name}' created")
            result_models = result.get("models", [])
            if result_models and isinstance(result_models[0], dict):
                model_text = f"{len(result_models)} model(s)"
            else:
                model_text = ", ".join(str(m) for m in model_list)
            details = {
                "ID": str(result.get("id", "—")),
                "Name": result.get("name", name),
                "Strategy": (result.get("strategy", strategy) or "").replace("_", " ").title(),
                "Models": model_text,
            }
            print_dict_as_table(details, title="Policy Details")
    except APIError as exc:
        print_error(f"Failed to create policy: {exc}")


# ── info ────────────────────────────────────────────────────────


@app.command("info")
def policy_info(
    policy_id: str = typer.Argument(..., help="Policy UUID"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Show detailed information about a routing policy."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching policy…[/cyan]"):
            p = api.get(f"{_RP}/{policy_id}")

        if fmt == "json":
            console.print_json(_json.dumps(p, default=str))
        else:
            info = {
                "ID": str(p.get("id", "—")),
                "Name": p.get("name", "—"),
                "Description": p.get("description", "—") or "—",
                "Strategy": (p.get("strategy", "—") or "—").replace("_", " ").title(),
                "Active": "✓" if p.get("enabled", p.get("is_active", True)) else "✗",
                "API Key Prefix": p.get("api_key_prefix", "—"),
                "Created": p.get("created_at", "—"),
            }
            print_dict_as_table(info, title=f"🎯 {p.get('name', 'Policy')}")

            model_names = p.get("model_names", {})
            models = p.get("models", p.get("model_ids", []))
            if models:
                rows = []
                for m in models:
                    if isinstance(m, dict):
                        mid = str(m.get("model_id", "—"))
                        display = model_names.get(mid, mid[:12] + "…")
                        rows.append({
                            "Model": display,
                            "Weight": f"{m.get('weight', '—')}%",
                            "Role": m.get("role", "—"),
                        })
                    else:
                        display = model_names.get(str(m), str(m))
                        rows.append({"Model": display})
                print_table(rows, title="Models")

            rules = p.get("rules", {})
            if rules and any(v is not None for v in rules.values()):
                rule_info = {}
                if rules.get("max_cost_per_request") is not None:
                    rule_info["Max Cost/Request"] = f"${rules['max_cost_per_request']}"
                if rules.get("max_tokens") is not None:
                    rule_info["Max Tokens"] = str(rules["max_tokens"])
                if rules.get("region_preference"):
                    rule_info["Region Preference"] = rules["region_preference"]
                if rule_info:
                    print_dict_as_table(rule_info, title="Rules")
    except APIError as exc:
        print_error(f"Failed to get policy: {exc}")


# ── test ────────────────────────────────────────────────────────


@app.command("test")
def test_policy(
    policy_id: str = typer.Argument(..., help="Policy UUID"),
    prompt: str = typer.Argument(..., help="Test prompt"),
    json_output: bool = typer.Option(False, "--json"),
):
    """
    Dry-run a routing policy with a sample prompt.

    Example:
        bonito policies test <policy-id> "What is machine learning?"
    """
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Testing policy…[/cyan]"):
            result = api.post(f"{_RP}/{policy_id}/test", {"prompt": prompt})

        if fmt == "json":
            console.print_json(_json.dumps(result, default=str))
        else:
            console.print("\n[bold green]🧪 Policy Test[/bold green]")
            info = {
                "Selected Model": result.get("selected_model_name", result.get("selected_model", "—")),
                "Model ID": str(result.get("selected_model_id", "—"))[:12] + "…",
                "Strategy": (result.get("strategy_used", result.get("strategy", "—")) or "—").replace("_", " ").title(),
                "Reasoning": result.get("selection_reason", result.get("reasoning", "—")),
            }
            est_cost = result.get("estimated_cost")
            if est_cost is not None:
                info["Est. Cost"] = format_cost(est_cost)
            est_latency = result.get("estimated_latency_ms")
            if est_latency is not None:
                info["Est. Latency"] = f"{est_latency}ms"
            print_dict_as_table(info, title="Result")
            print_info("Dry-run — no actual API call was made")
    except APIError as exc:
        print_error(f"Policy test failed: {exc}")


# ── stats ───────────────────────────────────────────────────────


@app.command("stats")
def policy_stats(
    policy_id: str = typer.Argument(..., help="Policy UUID"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Show usage statistics for a routing policy."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching stats…[/cyan]"):
            stats = api.get(f"{_RP}/{policy_id}/stats")

        if fmt == "json":
            console.print_json(_json.dumps(stats, default=str))
        else:
            info = {
                "Total Requests": f"{stats.get('request_count', stats.get('total_requests', 0)):,}",
                "Last 24h": f"{stats.get('last_24h_requests', 0):,}",
                "Success Rate": f"{stats.get('success_rate', 0):.1f}%",
                "Avg Latency": f"{stats.get('avg_latency_ms', 0):.0f}ms",
                "Total Cost": format_cost(stats.get("total_cost", 0)),
            }
            print_dict_as_table(info, title=f"📊 Policy Stats")

            dist = stats.get("model_distribution", {})
            if dist:
                # model_distribution is {model_id: request_count}
                if isinstance(dist, dict):
                    total = sum(dist.values()) or 1
                    rows = [
                        {
                            "Model": mid[:12] + "…",
                            "Requests": f"{count:,}",
                            "%": f"{(count / total * 100):.1f}%",
                        }
                        for mid, count in dist.items()
                    ]
                else:
                    rows = [
                        {"Model": d.get("model", "—") if isinstance(d, dict) else str(d), "Requests": f"{d.get('requests', 0):,}" if isinstance(d, dict) else "—"}
                        for d in dist
                    ]
                print_table(rows, title="Model Distribution")
    except APIError as exc:
        print_error(f"Failed to get policy stats: {exc}")


# ── delete ──────────────────────────────────────────────────────


@app.command("delete")
def delete_policy(
    policy_id: str = typer.Argument(..., help="Policy UUID"),
    force: bool = typer.Option(False, "--force", "-f"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Delete a routing policy."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    if not force and fmt != "json":
        if not typer.confirm(f"Delete policy {policy_id[:8]}…?"):
            print_info("Cancelled")
            return

    try:
        api.delete(f"{_RP}/{policy_id}")
        if fmt == "json":
            console.print_json(f'{{"status":"deleted","id":"{policy_id}"}}')
        else:
            print_success(f"Policy {policy_id[:8]}… deleted")
    except APIError as exc:
        print_error(f"Delete failed: {exc}")
