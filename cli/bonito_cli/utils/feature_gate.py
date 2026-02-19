"""
Feature gate utilities for CLI commands
"""
import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ..api import api, APIError
from .auth import ensure_authenticated

console = Console()


class FeatureAccessError(Exception):
    """Raised when a feature is not available on current tier"""
    pass


def require_feature(feature: str):
    """Check if current organization has access to a feature"""
    ensure_authenticated()
    
    try:
        response = api.get(f"/api/subscriptions/features?feature={feature}")
        
        if not response.get("has_access", False):
            # Show upgrade message
            current_tier = response.get("current_tier", "unknown")
            required_tier = response.get("required_tier", "pro")
            
            tier_display = {
                "free": "Free",
                "pro": "Pro", 
                "enterprise": "Enterprise"
            }
            
            current_name = tier_display.get(current_tier, current_tier.title())
            required_name = tier_display.get(required_tier, required_tier.title())
            
            # Create upgrade message
            upgrade_text = Text()
            upgrade_text.append("⚡ ", style="yellow bold")
            upgrade_text.append(f"This feature requires a {required_name} plan.\n", style="white")
            upgrade_text.append(f"You're currently on the {current_name} plan.\n\n", style="dim")
            upgrade_text.append("Run ", style="white")
            upgrade_text.append("bonito upgrade", style="cyan bold")
            upgrade_text.append(" or visit ", style="white")
            upgrade_text.append("https://getbonito.com/pricing", style="blue underline")
            
            panel = Panel(
                upgrade_text,
                title="🔒 Feature Not Available",
                border_style="yellow",
                padding=(1, 2),
            )
            
            console.print(panel)
            raise typer.Exit(1)
            
    except APIError as e:
        if e.status_code == 403:
            console.print(f"[red]Feature '{feature}' is not available on your current plan.[/red]")
            console.print(f"[dim]Run 'bonito upgrade' or visit https://getbonito.com/pricing[/dim]")
        else:
            console.print(f"[red]Error checking feature access: {e}[/red]")
        raise typer.Exit(1)


def require_tier(min_tier: str):
    """Check if current organization has minimum subscription tier"""
    ensure_authenticated()
    
    try:
        response = api.get("/api/subscriptions/current")
        current_tier = response.get("tier", "free")
        
        tier_hierarchy = {"free": 0, "pro": 1, "enterprise": 2}
        current_level = tier_hierarchy.get(current_tier, 0)
        required_level = tier_hierarchy.get(min_tier, 2)
        
        if current_level < required_level:
            tier_display = {
                "free": "Free",
                "pro": "Pro", 
                "enterprise": "Enterprise"
            }
            
            current_name = tier_display.get(current_tier, current_tier.title())
            required_name = tier_display.get(min_tier, min_tier.title())
            
            # Create upgrade message
            upgrade_text = Text()
            upgrade_text.append("⚡ ", style="yellow bold")
            upgrade_text.append(f"This feature requires a {required_name} plan.\n", style="white")
            upgrade_text.append(f"You're currently on the {current_name} plan.\n\n", style="dim")
            upgrade_text.append("Run ", style="white")
            upgrade_text.append("bonito upgrade", style="cyan bold")
            upgrade_text.append(" or visit ", style="white")
            upgrade_text.append("https://getbonito.com/pricing", style="blue underline")
            
            panel = Panel(
                upgrade_text,
                title="🔒 Feature Not Available",
                border_style="yellow",
                padding=(1, 2),
            )
            
            console.print(panel)
            raise typer.Exit(1)
            
    except APIError as e:
        if e.status_code == 403:
            console.print(f"[red]This feature requires a {min_tier.title()} plan.[/red]")
            console.print(f"[dim]Run 'bonito upgrade' or visit https://getbonito.com/pricing[/dim]")
        else:
            console.print(f"[red]Error checking subscription tier: {e}[/red]")
        raise typer.Exit(1)


def get_subscription_info():
    """Get current subscription information"""
    ensure_authenticated()
    
    try:
        return api.get("/api/subscriptions/current")
    except APIError as e:
        console.print(f"[red]Error getting subscription info: {e}[/red]")
        raise typer.Exit(1)


def show_usage_summary():
    """Show usage summary for current organization"""
    ensure_authenticated()
    
    try:
        response = api.get("/api/subscriptions/usage")
        usage = response.get("usage", {})
        
        console.print("\n[bold]Usage Summary[/bold]")
        console.print("─" * 50)
        
        for limit_type, info in usage.items():
            limit_name = {
                "providers": "Providers",
                "members": "Team Members",
                "gateway_calls_per_month": "Gateway Calls (Monthly)"
            }.get(limit_type, limit_type.replace("_", " ").title())
            
            current = info.get("current", 0)
            limit_val = info.get("limit", "unlimited")
            remaining = info.get("remaining", "unlimited")
            
            if limit_val == "unlimited":
                console.print(f"  {limit_name}: {current} (unlimited)")
            else:
                percentage = (current / limit_val) * 100 if limit_val > 0 else 0
                color = "red" if percentage >= 90 else "yellow" if percentage >= 80 else "green"
                console.print(f"  {limit_name}: {current}/{limit_val} [{color}]{percentage:.1f}%[/{color}]")
        
        console.print()
        
    except APIError as e:
        console.print(f"[red]Error getting usage info: {e}[/red]")