"""Analytics and usage insights commands."""

from __future__ import annotations

import json as _json
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.feature_gate import require_feature
from ..utils.display import (
    format_cost,
    format_tokens,
    get_output_format,
    print_dict_as_table,
    print_error,
    print_info,
    print_table,
)

console = Console()
app = typer.Typer(help="📊 Usage analytics & costs")


# ── overview ────────────────────────────────────────────────────


@app.command("overview")
def overview(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Show the analytics dashboard overview.

    Displays key metrics, top models, and recent activity.
    """
    fmt = get_output_format(json_output)
    ensure_authenticated()
    require_feature("analytics")

    try:
        with console.status("[cyan]Fetching analytics…[/cyan]"):
            data = api.get("/analytics/overview")

        if fmt == "json":
            console.print_json(_json.dumps(data, default=str))
            return

        # Key metrics
        m = data.get("metrics", data)
        metrics_text = (
            f"[bold green]Requests:[/bold green]     {m.get('total_requests', 0):,}\n"
            f"[bold green]Cost:[/bold green]         ${m.get('total_cost', 0):.2f}\n"
            f"[bold green]Tokens:[/bold green]       {format_tokens(m.get('total_tokens', 0))}\n"
            f"[bold green]Success rate:[/bold green] {m.get('success_rate', 0):.1f}%\n"
            f"[bold green]Avg latency:[/bold green]  {m.get('avg_latency_ms', 0):.0f}ms"
        )
        console.print(Panel(metrics_text, title="📊 Key Metrics (30 days)", border_style="green"))

        # Top models
        top = data.get("top_models", [])
        if top:
            rows = [
                {
                    "Model": tm.get("id", tm.get("model", "—")),
                    "Requests": f"{tm.get('requests', 0):,}",
                    "Cost": format_cost(tm.get("cost", 0)),
                }
                for tm in top[:5]
            ]
            print_table(rows, title="🔥 Top Models")

        # Recent activity
        recent = data.get("recent_activity", {})
        if recent:
            ra = {
                "Requests (24h)": f"{recent.get('requests_24h', 0):,}",
                "Cost (24h)": format_cost(recent.get("cost_24h", 0)),
                "Peak hour": recent.get("peak_hour", "—"),
            }
            print_dict_as_table(ra, title="📈 Recent Activity")

    except APIError as exc:
        print_error(f"Failed to get overview: {exc}")


# ── usage ───────────────────────────────────────────────────────


@app.command("usage")
def usage(
    period: str = typer.Option("week", "--period", "-p", help="day / week / month"),
    json_output: bool = typer.Option(False, "--json"),
):
    """
    Show detailed usage analytics.

    Examples:
        bonito analytics usage
        bonito analytics usage --period month
    """
    fmt = get_output_format(json_output)
    ensure_authenticated()

    if period not in ("day", "week", "month"):
        print_error("--period must be day, week, or month")
        return

    try:
        with console.status("[cyan]Fetching usage data…[/cyan]"):
            data = api.get("/analytics/usage", params={"period": period})

        if fmt == "json":
            console.print_json(_json.dumps(data, default=str))
            return

        summary = data.get("summary", data)
        info = {
            "Period": period.title(),
            "Total Requests": f"{summary.get('total_requests', 0):,}",
            "Total Tokens": format_tokens(summary.get("total_tokens", 0)),
            "Total Cost": format_cost(summary.get("total_cost", 0)),
            "Unique Models": summary.get("unique_models", "—"),
        }
        print_dict_as_table(info, title=f"📈 Usage ({period.title()})")

        ts = data.get("time_series", [])
        if ts:
            rows = [
                {
                    "Date": p.get("date", "—"),
                    "Requests": f"{p.get('requests', 0):,}",
                    "Tokens": format_tokens(p.get("tokens", 0)),
                    "Cost": format_cost(p.get("cost", 0)),
                }
                for p in ts[-10:]
            ]
            print_table(rows, title="Time Series")

    except APIError as exc:
        print_error(f"Failed to get usage: {exc}")


# ── costs ───────────────────────────────────────────────────────


@app.command("costs")
def costs(
    period: Optional[str] = typer.Option(None, "--period", help="daily / weekly / monthly"),
    json_output: bool = typer.Option(False, "--json"),
):
    """
    Show cost analytics and breakdown.

    Examples:
        bonito analytics costs
        bonito analytics costs --period monthly
    """
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        params = {"period": period} if period else None
        with console.status("[cyan]Fetching cost data…[/cyan]"):
            data = api.get("/analytics/costs", params=params)

        if fmt == "json":
            console.print_json(_json.dumps(data, default=str))
            return

        summary = data.get("summary", data)
        total = summary.get("total_cost", 0)
        # total_cost might be at top level (not in summary)
        if total == 0:
            # Sum from by_provider or by_model if summary didn't have it
            for p in data.get("by_provider", []):
                total += p.get("cost", 0)
        console.print(f"\n[bold green]💰 Total cost:[/bold green] ${total:.2f}")

        # By model — check both nested (breakdown.by_model) and top-level
        breakdown = data.get("breakdown", {})
        by_model = breakdown.get("by_model", data.get("by_model", []))
        if by_model:
            rows = [
                {
                    "Model": mc.get("model", "—"),
                    "Cost": format_cost(mc.get("cost", 0)),
                    "Requests": f"{mc.get('requests', 0):,}",
                    "Tokens": format_tokens(mc.get("tokens", 0)),
                    "Share": f"{(mc.get('cost', 0) / total * 100):.1f}%" if total else "0%",
                }
                for mc in by_model
            ]
            print_table(rows, title="💸 Cost by Model")

        # By provider — check both nested and top-level
        by_prov = breakdown.get("by_provider", data.get("by_provider", []))
        if by_prov:
            rows = [
                {
                    "Provider": pc.get("provider", "—"),
                    "Cost": format_cost(pc.get("cost", 0)),
                    "Share": f"{(pc.get('cost', 0) / total * 100):.1f}%" if total else "0%",
                }
                for pc in by_prov
            ]
            print_table(rows, title="☁️  Cost by Provider")

        # Trends
        trends = data.get("trends", {})
        if trends:
            ti = {
                "This Period": format_cost(trends.get("current_period", 0)),
                "Previous": format_cost(trends.get("previous_period", 0)),
                "Change": f"{trends.get('change_percent', 0):+.1f}%",
                "Projected Monthly": format_cost(trends.get("projected_monthly", 0)),
            }
            print_dict_as_table(ti, title="📊 Trends")

        # Suggestions
        suggestions = data.get("optimization_suggestions", [])
        if suggestions:
            console.print("\n[bold yellow]💡 Optimisation tips:[/bold yellow]")
            for s in suggestions:
                console.print(f"  • {s.get('message', s)}")

    except APIError as exc:
        print_error(f"Failed to get cost data: {exc}")


# ── trends ──────────────────────────────────────────────────────


@app.command("trends")
def trends(
    json_output: bool = typer.Option(False, "--json"),
):
    """Show usage and performance trend analysis."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Analysing trends…[/cyan]"):
            data = api.get("/analytics/trends")

        if fmt == "json":
            console.print_json(_json.dumps(data, default=str))
            return

        console.print("\n[bold cyan]📈 Trend Analysis[/bold cyan]\n")

        ut = data.get("usage_trends", {})
        if ut:
            info = {
                "Requests": f"{ut.get('requests_trend', 0):+.1f}% vs last month",
                "Tokens": f"{ut.get('tokens_trend', 0):+.1f}% vs last month",
                "Growth": f"{ut.get('growth_rate', 0):.1f}% monthly",
            }
            print_dict_as_table(info, title="Usage Trends")

        mt = data.get("model_trends", [])
        if mt:
            rows = []
            for t in mt:
                arrow = "📈" if t.get("change_percent", 0) > 0 else "📉"
                rows.append({
                    "Model": t.get("model", "—"),
                    "Trend": f"{arrow} {abs(t.get('change_percent', 0)):.1f}%",
                    "Share": f"{t.get('current_share', 0):.1f}%",
                })
            print_table(rows, title="🤖 Model Adoption")

        pt = data.get("performance_trends", {})
        if pt:
            pi = {
                "Latency": f"{pt.get('latency_trend', 0):+.1f}%",
                "Success rate": f"{pt.get('success_rate_trend', 0):+.1f}%",
                "Error rate": f"{pt.get('error_rate_trend', 0):+.1f}%",
            }
            print_dict_as_table(pi, title="⚡ Performance")

        insights = data.get("insights", [])
        if insights:
            console.print("\n[bold blue]🔍 Insights:[/bold blue]")
            for i in insights:
                console.print(f"  • {i.get('message', i)}")

    except APIError as exc:
        print_error(f"Failed to get trends: {exc}")


# ── digest ──────────────────────────────────────────────────────


@app.command("digest")
def digest(
    json_output: bool = typer.Option(False, "--json"),
):
    """Generate a weekly analytics digest report."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Generating digest…[/cyan]"):
            data = api.get("/analytics/digest")

        if fmt == "json":
            console.print_json(_json.dumps(data, default=str))
            return

        console.print(f"\n[bold cyan]📋 Weekly Digest[/bold cyan]")
        console.print(f"[dim]{data.get('period', 'Last 7 days')}[/dim]\n")

        # Support both 'executive_summary' and 'summary' from backend
        s = data.get("executive_summary", data.get("summary", {}))
        if s:
            text = (
                f"[bold green]Requests:[/bold green]     {s.get('total_requests', 0):,}"
                f"  ({s.get('cost_change_pct', s.get('requests_change', 0)):+.1f}%)\n"
                f"[bold green]Cost:[/bold green]         ${s.get('total_cost', 0):.2f}\n"
                f"[bold green]Top Model:[/bold green]    {s.get('top_model', '—')}"
                f"  ({s.get('top_model_pct', 0):.1f}%)\n"
                f"[bold green]Active Users:[/bold green] {s.get('active_users', 0)}"
            )
            console.print(Panel(text, title="Week at a Glance", border_style="green"))

        tp = data.get("top_performers", {})
        if tp:
            console.print("[bold]🏆 Top Performers:[/bold]")
            console.print(f"  Most used:          [cyan]{tp.get('most_used_model', '—')}[/cyan]")
            console.print(f"  Fastest:            [cyan]{tp.get('fastest_model', '—')}[/cyan]")
            console.print(f"  Most cost-effective: [cyan]{tp.get('most_cost_effective', '—')}[/cyan]")

        highlights = data.get("highlights", [])
        if highlights:
            console.print("\n[bold yellow]✨ Highlights:[/bold yellow]")
            for h in highlights:
                console.print(f"  • {h if isinstance(h, str) else h.get('message', h)}")

        recs = data.get("recommendations", [])
        if recs:
            console.print("\n[bold blue]💡 Recommendations:[/bold blue]")
            for r in recs:
                console.print(f"  • {r if isinstance(r, str) else r.get('message', r)}")

    except APIError as exc:
        print_error(f"Failed to generate digest: {exc}")
