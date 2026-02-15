"""Authentication commands for Bonito CLI."""

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table
from typing import Optional

from ..api import api, APIError
from ..config import save_credentials, clear_credentials, is_authenticated, load_credentials

console = Console()
app = typer.Typer(help="🔐 Authentication & account management")


@app.command("login")
def login(
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Account email"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Account password"),
    api_url: Optional[str] = typer.Option(None, "--api-url", help="Custom API URL"),
):
    """
    Login to Bonito with email and password.
    
    Example:
        bonito auth login
        bonito auth login --email admin@company.com
    """
    if not email:
        email = Prompt.ask("[cyan]Email[/cyan]")
    if not password:
        password = Prompt.ask("[cyan]Password[/cyan]", password=True)
    
    if not email or not password:
        console.print("[red]Email and password are required[/red]")
        raise typer.Exit(1)
    
    # Override API URL if provided
    if api_url:
        from ..config import set_config_value
        set_config_value("api_url", api_url)
        api.base_url = api_url
    
    try:
        with console.status("[cyan]Authenticating...[/cyan]"):
            import httpx, asyncio
            resp = httpx.post(
                f"{api.base_url}/api/auth/login",
                json={"email": email, "password": password},
                timeout=15,
            )
        
        if resp.status_code != 200:
            error = resp.json().get("detail", "Login failed")
            console.print(f"[red]✗ {error}[/red]")
            raise typer.Exit(1)
        
        data = resp.json()
        save_credentials({
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "email": email,
        })
        
        # Fetch user info
        try:
            me = api.get("/auth/me")
            save_credentials({
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token"),
                "email": email,
                "user": me,
            })
            org_name = me.get("org", {}).get("name", "")
            console.print(Panel(
                f"[green]✓ Logged in as [bold]{email}[/bold][/green]\n"
                f"  Organization: {org_name}\n"
                f"  Role: {me.get('role', 'member')}",
                title="🔐 Authenticated",
                border_style="green",
            ))
        except Exception:
            console.print(f"[green]✓ Logged in as {email}[/green]")
    
    except httpx.RequestError as e:
        console.print(f"[red]✗ Connection failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("logout")
def logout():
    """Log out and clear stored credentials."""
    clear_credentials()
    console.print("[green]✓ Logged out successfully[/green]")


@app.command("whoami")
def whoami():
    """Show current authenticated user."""
    if not is_authenticated():
        console.print("[yellow]Not logged in. Run: bonito auth login[/yellow]")
        raise typer.Exit(1)
    
    try:
        me = api.get("/auth/me")
        table = Table(show_header=False, border_style="dim")
        table.add_column("Key", style="cyan")
        table.add_column("Value")
        table.add_row("Email", me.get("email", "—"))
        table.add_row("Name", me.get("name", "—"))
        table.add_row("Role", me.get("role", "—"))
        table.add_row("Organization", me.get("org", {}).get("name", "—"))
        table.add_row("Org ID", str(me.get("org_id", "—"))[:8] + "...")
        console.print(Panel(table, title="👤 Current User", border_style="cyan"))
    except APIError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)


@app.command("status")
def status():
    """Check authentication status and API connectivity."""
    creds = load_credentials()
    
    if not creds.get("access_token"):
        console.print("[red]✗ Not authenticated[/red]")
        console.print("  Run: [cyan]bonito auth login[/cyan]")
        raise typer.Exit(1)
    
    console.print(f"[green]✓ Token stored[/green] ({creds.get('email', 'unknown')})")
    
    try:
        with console.status("[cyan]Checking API...[/cyan]"):
            me = api.get("/auth/me")
        console.print(f"[green]✓ API reachable[/green] — {me.get('email', '')}")
    except APIError as e:
        console.print(f"[red]✗ API error: {e}[/red]")
        if "401" in str(e) or "Authentication" in str(e):
            console.print("  Token may be expired. Run: [cyan]bonito auth login[/cyan]")
