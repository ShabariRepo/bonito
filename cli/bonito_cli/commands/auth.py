"""Authentication commands."""

from __future__ import annotations

from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from ..api import api, APIError
from ..config import (
    clear_credentials,
    is_authenticated,
    load_credentials,
    save_credentials,
    set_config_value,
)

console = Console()
app = typer.Typer(help="🔐 Authentication & account management")


# ── signup ──────────────────────────────────────────────────────


@app.command("signup")
def signup(
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Account email"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Account password"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Full name"),
    org: Optional[str] = typer.Option(None, "--org", "-o", help="Organization name"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Non-interactive mode (requires all fields as flags)"),
    api_url: Optional[str] = typer.Option(None, "--api-url", help="Custom API URL"),
):
    """
    Sign up for a new Bonito account.

    Examples:
        bonito auth signup
        bonito auth signup --email admin@company.com --name "John Doe" --org "ACME Corp"
        bonito auth signup --non-interactive --email admin@company.com --password secret --name "John Doe" --org "ACME Corp"
    """
    # In non-interactive mode, all fields must be provided as flags
    if non_interactive:
        if not all([email, password, name, org]):
            console.print("[red]✗ In non-interactive mode, all fields (--email, --password, --name, --org) are required[/red]")
            raise typer.Exit(1)
    else:
        # Interactive prompts
        if not email:
            email = Prompt.ask("[cyan]Email[/cyan]")
        if not password:
            password = Prompt.ask("[cyan]Password[/cyan]", password=True)
        if not name:
            name = Prompt.ask("[cyan]Full name[/cyan]")
        if not org:
            org = Prompt.ask("[cyan]Organization name[/cyan]")

    if not all([email, password, name, org]):
        console.print("[red]✗ All fields (email, password, name, organization) are required[/red]")
        raise typer.Exit(1)

    # Allow overriding the API URL
    if api_url:
        set_config_value("api_url", api_url)
        api.base_url = api_url
        # Force new client with the new base_url
        if api._client and not api._client.is_closed:
            api._client.close()
        api._client = None

    try:
        with console.status("[cyan]Creating account…[/cyan]"):
            resp = httpx.post(
                f"{api.base_url}/api/auth/register",
                json={
                    "email": email,
                    "password": password,
                    "name": name,
                },
                timeout=15,
            )

        if resp.status_code != 200:
            detail = "Registration failed"
            try:
                detail = resp.json().get("detail", detail)
            except Exception:
                pass
            console.print(f"[red]✗ {detail}[/red]")
            raise typer.Exit(1)

        data = resp.json()
        
        # Auto-login after successful signup
        creds = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "email": email,
        }
        save_credentials(creds)

        # Fetch user profile
        try:
            me = api.get("/auth/me")
            creds["user"] = me
            save_credentials(creds)
            org_name = me.get("org", {}).get("name", "—")
            console.print(
                Panel(
                    f"[green]✓ Account created and logged in as [bold]{email}[/bold][/green]\n"
                    f"  Organization: {org_name}\n"
                    f"  Role: {me.get('role', 'member')}",
                    title="🎉 Welcome to Bonito",
                    border_style="green",
                )
            )
        except Exception:
            console.print(f"[green]✓ Account created and logged in as {email}[/green]")

    except httpx.RequestError as exc:
        console.print(f"[red]✗ Connection failed: {exc}[/red]")
        raise typer.Exit(1)


# ── login ───────────────────────────────────────────────────────


@app.command("login")
def login(
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Account email"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Account password"),
    api_url: Optional[str] = typer.Option(None, "--api-url", help="Custom API URL"),
):
    """
    Log in to Bonito with email and password.

    Examples:
        bonito auth login
        bonito auth login --email admin@company.com
    """
    if not email:
        email = Prompt.ask("[cyan]Email[/cyan]")
    if not password:
        password = Prompt.ask("[cyan]Password[/cyan]", password=True)

    if not email or not password:
        console.print("[red]✗ Email and password are required[/red]")
        raise typer.Exit(1)

    # Allow overriding the API URL
    if api_url:
        set_config_value("api_url", api_url)
        api.base_url = api_url
        # Force new client with the new base_url
        if api._client and not api._client.is_closed:
            api._client.close()
        api._client = None

    try:
        with console.status("[cyan]Authenticating…[/cyan]"):
            resp = httpx.post(
                f"{api.base_url}/api/auth/login",
                json={"email": email, "password": password},
                timeout=15,
            )

        if resp.status_code != 200:
            detail = "Login failed"
            try:
                detail = resp.json().get("detail", detail)
            except Exception:
                pass
            console.print(f"[red]✗ {detail}[/red]")
            raise typer.Exit(1)

        data = resp.json()
        creds = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "email": email,
        }
        save_credentials(creds)

        # Fetch user profile
        try:
            me = api.get("/auth/me")
            creds["user"] = me
            save_credentials(creds)
            org_name = me.get("org", {}).get("name", "—")
            console.print(
                Panel(
                    f"[green]✓ Logged in as [bold]{email}[/bold][/green]\n"
                    f"  Organization: {org_name}\n"
                    f"  Role: {me.get('role', 'member')}",
                    title="🔐 Authenticated",
                    border_style="green",
                )
            )
        except Exception:
            console.print(f"[green]✓ Logged in as {email}[/green]")

    except httpx.RequestError as exc:
        console.print(f"[red]✗ Connection failed: {exc}[/red]")
        raise typer.Exit(1)


# ── logout ──────────────────────────────────────────────────────


@app.command("logout")
def logout():
    """Log out and clear stored credentials."""
    clear_credentials()
    console.print("[green]✓ Logged out successfully[/green]")


# ── whoami ──────────────────────────────────────────────────────


@app.command("whoami")
def whoami():
    """Show the current authenticated user."""
    if not is_authenticated():
        console.print("[yellow]Not logged in. Run: bonito auth login[/yellow]")
        raise typer.Exit(1)

    try:
        with console.status("[cyan]Fetching profile…[/cyan]"):
            me = api.get("/auth/me")

        table = Table(show_header=False, border_style="dim")
        table.add_column("Field", style="cyan")
        table.add_column("Value")
        table.add_row("Email", me.get("email", "—"))
        table.add_row("Name", me.get("name", "—"))
        table.add_row("Role", me.get("role", "—"))
        table.add_row("Organization", me.get("org", {}).get("name", "—"))
        org_id = str(me.get("org_id", "—"))
        table.add_row("Org ID", org_id[:8] + "…" if len(org_id) > 8 else org_id)
        console.print(Panel(table, title="👤 Current User", border_style="cyan"))

    except APIError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)


# ── status ──────────────────────────────────────────────────────


@app.command("status")
def status():
    """Check authentication status and API connectivity."""
    creds = load_credentials()

    if not creds.get("access_token"):
        console.print("[red]✗ Not authenticated[/red]")
        console.print("  Run: [cyan]bonito auth login[/cyan]")
        raise typer.Exit(1)

    console.print(f"[green]✓ Token stored[/green]  ({creds.get('email', 'unknown')})")

    try:
        with console.status("[cyan]Checking API…[/cyan]"):
            me = api.get("/auth/me")
        console.print(f"[green]✓ API reachable[/green]  — {me.get('email', '')}")
    except APIError as exc:
        console.print(f"[red]✗ API error: {exc}[/red]")
        if exc.status_code == 401:
            console.print("  Token may be expired. Run: [cyan]bonito auth login[/cyan]")
