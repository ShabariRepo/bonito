"""Subscription plan and usage commands."""

from __future__ import annotations

import json as _json
import webbrowser
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.display import get_output_format, print_error
from ..utils.feature_gate import get_subscription_info, show_usage_summary

console = Console()
app = typer.Typer(help="💎 Subscription plans & usage")


@app.command("show")
def show_plan(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Show current subscription plan and usage.
    """
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching subscription info…[/cyan]"):
            data = get_subscription_info()

        if fmt == "json":
            console.print_json(_json.dumps(data, default=str))
            return

        # Display current plan
        tier = data.get("tier", "unknown")
        status = data.get("status", "unknown")
        bonobot_plan = data.get("bonobot_plan", "none")
        bonobot_limit = data.get("bonobot_agent_limit", 0)
        
        tier_display = {
            "free": "Free",
            "starter": "Starter",
            "pro": "Pro",
            "enterprise": "Enterprise"
        }
        
        status_display = {
            "active": "✅ Active",
            "trial": "🆓 Trial",
            "expired": "❌ Expired",
            "cancelled": "🚫 Cancelled"
        }
        
        # Plan info panel
        plan_text = Text()
        plan_text.append(f"{tier_display.get(tier, tier.title())} Plan\n", style="bold cyan")
        plan_text.append(f"Status: {status_display.get(status, status.title())}\n", style="white")
        
        if bonobot_plan != "none":
            bonobot_display = {
                "hosted": "Hosted",
                "vpc": "VPC"
            }
            plan_text.append(f"Bonobot: {bonobot_display.get(bonobot_plan, bonobot_plan.title())}")
            if bonobot_limit > 0:
                plan_text.append(f" ({bonobot_limit} agents)")
            plan_text.append("\n")

        panel = Panel(
            plan_text,
            title="📋 Current Plan",
            border_style="cyan",
            padding=(1, 2),
        )
        console.print(panel)

        # Show tier limits
        tier_limits = data.get("tier_limits", {})
        if tier_limits:
            console.print("\n[bold]Plan Limits[/bold]")
            
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Feature")
            table.add_column("Limit")
            
            # Display limits
            providers_limit = tier_limits.get("providers", 0)
            calls_limit = tier_limits.get("gateway_calls_per_month", 0)
            members_limit = tier_limits.get("members", 0)
            
            table.add_row("Providers", "Unlimited" if providers_limit == float('inf') else str(providers_limit))
            table.add_row("Gateway Calls/Month", "Unlimited" if calls_limit == float('inf') else f"{calls_limit:,}")
            table.add_row("Team Members", "Unlimited" if members_limit == float('inf') else str(members_limit))
            
            console.print(table)

        # Show usage summary
        show_usage_summary()

    except APIError as e:
        print_error(f"Failed to fetch subscription info: {e}")
        raise typer.Exit(1)


@app.command("features")
def show_features(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Show feature comparison across all tiers.
    """
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching tier comparison…[/cyan]"):
            data = api.get("/api/subscriptions/tiers")

        if fmt == "json":
            console.print_json(_json.dumps(data, default=str))
            return

        current_tier = data.get("current_tier", "free")
        tiers = data.get("tiers", {})
        
        console.print(f"\n[bold]Feature Comparison[/bold] (Current: [cyan]{current_tier.title()}[/cyan])")
        
        table = Table(show_header=True, header_style="bold")
        table.add_column("Feature")
        table.add_column("Free", style="dim" if current_tier != "free" else "bold green")
        table.add_column("Starter", style="dim" if current_tier != "starter" else "bold green")
        table.add_column("Pro", style="dim" if current_tier != "pro" else "bold green")
        table.add_column("Enterprise", style="dim" if current_tier != "enterprise" else "bold green")

        # Feature mapping for display
        feature_names = {
            "models": "AI Models",
            "playground": "Playground",
            "routing": "Routing Policies",
            "ai_context": "AI Context",
            "analytics": "Analytics",
            "cli": "CLI Access",
            "audit": "Audit Logs",
            "notifications": "Notifications",
            "budget_alerts": "Budget Alerts",
            "sso": "SSO/SAML",
            "rbac": "RBAC",
            "iac_templates": "IaC Templates",
            "compliance": "Compliance",
            "on_premise": "On-Premise",
            "custom_integrations": "Custom Integrations",
            "dedicated_support": "Dedicated Support"
        }

        # Get features from one tier (they should all have the same keys)
        features = tiers.get("free", {}).get("features", {})

        for feature_key, display_name in feature_names.items():
            if feature_key in features:
                free_val = "✅" if tiers.get("free", {}).get("features", {}).get(feature_key, False) else "❌"
                starter_val = "✅" if tiers.get("starter", {}).get("features", {}).get(feature_key, False) else "❌"
                pro_val = "✅" if tiers.get("pro", {}).get("features", {}).get(feature_key, False) else "❌"
                ent_val = "✅" if tiers.get("enterprise", {}).get("features", {}).get(feature_key, False) else "❌"

                table.add_row(display_name, free_val, starter_val, pro_val, ent_val)
        
        console.print(table)

        # Show limits
        console.print("\n[bold]Limits[/bold]")
        
        limits_table = Table(show_header=True, header_style="bold")
        limits_table.add_column("Resource")
        limits_table.add_column("Free", style="dim" if current_tier != "free" else "bold green")
        limits_table.add_column("Starter", style="dim" if current_tier != "starter" else "bold green")
        limits_table.add_column("Pro", style="dim" if current_tier != "pro" else "bold green")
        limits_table.add_column("Enterprise", style="dim" if current_tier != "enterprise" else "bold green")

        # Providers
        free_providers = tiers.get("free", {}).get("providers", 0)
        starter_providers = tiers.get("starter", {}).get("providers", 0)
        pro_providers = tiers.get("pro", {}).get("providers", 0)
        ent_providers = tiers.get("enterprise", {}).get("providers", 0)

        limits_table.add_row(
            "Providers",
            str(free_providers) if free_providers != float('inf') else "Unlimited",
            str(starter_providers) if starter_providers != float('inf') else "Unlimited",
            str(pro_providers) if pro_providers != float('inf') else "Unlimited",
            str(ent_providers) if ent_providers != float('inf') else "Unlimited"
        )

        # Gateway calls
        free_calls = tiers.get("free", {}).get("gateway_calls", 0)
        starter_calls = tiers.get("starter", {}).get("gateway_calls", 0)
        pro_calls = tiers.get("pro", {}).get("gateway_calls", 0)
        ent_calls = tiers.get("enterprise", {}).get("gateway_calls", 0)

        limits_table.add_row(
            "Gateway Calls/Month",
            f"{free_calls:,}" if free_calls != float('inf') else "Unlimited",
            f"{starter_calls:,}" if starter_calls != float('inf') else "Unlimited",
            f"{pro_calls:,}" if pro_calls != float('inf') else "Unlimited",
            f"{ent_calls:,}" if ent_calls != float('inf') else "Unlimited"
        )

        # Members
        free_members = tiers.get("free", {}).get("members", 0)
        starter_members = tiers.get("starter", {}).get("members", 0)
        pro_members = tiers.get("pro", {}).get("members", 0)
        ent_members = tiers.get("enterprise", {}).get("members", 0)

        limits_table.add_row(
            "Team Members",
            str(free_members) if free_members != float('inf') else "Unlimited",
            str(starter_members) if starter_members != float('inf') else "Unlimited",
            str(pro_members) if pro_members != float('inf') else "Unlimited",
            str(ent_members) if ent_members != float('inf') else "Unlimited"
        )
        
        console.print(limits_table)

    except APIError as e:
        print_error(f"Failed to fetch tier comparison: {e}")
        raise typer.Exit(1)


@app.command("upgrade")
def upgrade():
    """
    Open the pricing page to upgrade your plan.
    """
    console.print("🚀 [bold cyan]Opening Bonito pricing page...[/bold cyan]")
    
    try:
        webbrowser.open("https://getbonito.com/pricing")
        console.print("✅ Pricing page opened in your browser!")
        console.print("💡 [dim]Contact us for Enterprise pricing and custom requirements.[/dim]")
    except Exception as e:
        console.print(f"❌ [red]Failed to open browser: {e}[/red]")
        console.print("🔗 [cyan]Please visit: https://getbonito.com/pricing[/cyan]")


@app.command("usage")
def show_usage(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Show detailed usage information.
    """
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching usage data…[/cyan]"):
            data = api.get("/api/subscriptions/usage")

        if fmt == "json":
            console.print_json(_json.dumps(data, default=str))
            return

        show_usage_summary()

    except APIError as e:
        print_error(f"Failed to fetch usage data: {e}")
        raise typer.Exit(1)