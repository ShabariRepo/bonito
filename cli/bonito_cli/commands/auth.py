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
from ..utils.auth import ensure_authenticated
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
    invite_code: Optional[str] = typer.Option(None, "--invite-code", "-i", help="Invite code (required for invite-only registration)"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Non-interactive mode (requires all fields as flags)"),
    api_url: Optional[str] = typer.Option(None, "--api-url", help="Custom API URL"),
):
    """
    Sign up for a new Bonito account.

    After signup you must verify your email before logging in.

    Examples:
        bonito auth signup
        bonito auth signup --invite-code ABC123
        bonito auth signup --email admin@company.com --name "John Doe" --org "ACME Corp" --invite-code ABC123
    """
    # In non-interactive mode, all fields must be provided as flags
    if non_interactive:
        if not all([email, password, name]):
            console.print("[red]✗ In non-interactive mode, --email, --password, and --name are required[/red]")
            raise typer.Exit(1)
    else:
        # Interactive prompts
        if not email:
            email = Prompt.ask("[cyan]Email[/cyan]")
        if not password:
            password = Prompt.ask("[cyan]Password[/cyan]", password=True)
        if not name:
            name = Prompt.ask("[cyan]Full name[/cyan]")
        if not invite_code:
            invite_code = Prompt.ask("[cyan]Invite code (leave blank if not required)[/cyan]", default="")
            if not invite_code:
                invite_code = None

    if not all([email, password, name]):
        console.print("[red]✗ Email, password, and name are required[/red]")
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
        body = {
            "email": email,
            "password": password,
            "name": name,
        }
        if invite_code:
            body["invite_code"] = invite_code

        with console.status("[cyan]Creating account…[/cyan]"):
            resp = httpx.post(
                f"{api.base_url}/api/auth/register",
                json=body,
                timeout=15,
            )

        if resp.status_code not in (200, 201):
            detail = "Registration failed"
            try:
                err = resp.json()
                detail = err.get("detail") or err.get("message", detail)
            except Exception:
                pass
            console.print(f"[red]✗ {detail}[/red]")
            raise typer.Exit(1)

        data = resp.json()
        message = data.get("message", "Account created")

        console.print(
            Panel(
                f"[green]✓ {message}[/green]\n\n"
                f"  Please verify your email, then run:\n"
                f"  [cyan]bonito auth login --email {email}[/cyan]",
                title="🎉 Welcome to Bonito",
                border_style="green",
            )
        )

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
        login_url = f"{api.base_url}/api/auth/login"
        with console.status("[cyan]Authenticating…[/cyan]"):
            resp = httpx.post(
                login_url,
                json={"email": email, "password": password},
                timeout=15,
            )

        if resp.status_code != 200:
            detail = "Login failed"
            try:
                body = resp.json()
                detail = body.get("detail") or body.get("message") or body.get("error", {}).get("message", detail)
            except Exception:
                detail = f"HTTP {resp.status_code}: {resp.text[:200]}"
            console.print(f"[red]✗ {detail}[/red]")
            raise typer.Exit(1)

        data = resp.json()
        creds = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "email": email,
        }
        save_credentials(creds)

        # Reset the HTTP client so it picks up the fresh token
        # (otherwise the client keeps using the old expired token)
        if api._client and not api._client.is_closed:
            api._client.close()
        api._client = None

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


# ── token management ─────────────────────────────────────────

token_app = typer.Typer(help="🔑 Personal access token management")
app.add_typer(token_app, name="token")


@token_app.command("create")
def token_create(
    name: str = typer.Option(..., "--name", "-n", help="Token name"),
    scopes: Optional[str] = typer.Option(None, "--scopes", "-s", help="Comma-separated scopes (omit for full access)"),
    expires_in: int = typer.Option(90, "--expires-in", help="Expiry in days (1-365)"),
):
    """Create a personal access token (bp-...)."""
    ensure_authenticated()

    body = {"name": name, "expires_in_days": expires_in}
    if scopes:
        body["scopes"] = [s.strip() for s in scopes.split(",")]

    try:
        with console.status("[cyan]Creating token…[/cyan]"):
            result = api.post("/tokens", json=body)

        raw_token = result.get("token", "")
        console.print(
            Panel(
                f"[green]✓ Token created[/green]\n\n"
                f"  [bold yellow]{raw_token}[/bold yellow]\n\n"
                f"  [dim]Copy this now — it won't be shown again.[/dim]\n"
                f"  Name: {result.get('name')}\n"
                f"  Prefix: {result.get('token_prefix')}\n"
                f"  Expires: {result.get('expires_at', '')[:10]}",
                title="🔑 Personal Access Token",
                border_style="green",
            )
        )
    except APIError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)


@token_app.command("list")
def token_list():
    """List your personal access tokens."""
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching tokens…[/cyan]"):
            tokens = api.get("/tokens")

        if not tokens:
            console.print("[yellow]No personal access tokens found.[/yellow]")
            console.print("  Create one: [cyan]bonito auth token create --name my-token[/cyan]")
            return

        table = Table(title="Personal Access Tokens", border_style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Prefix")
        table.add_column("Expires")
        table.add_column("Last Used")
        table.add_column("Status")
        table.add_column("ID", style="dim")

        for t in tokens:
            status_str = "[red]Revoked[/red]" if t.get("revoked_at") else "[green]Active[/green]"
            expires = t.get("expires_at", "")[:10]
            last_used = t.get("last_used_at", "")
            last_used = last_used[:10] if last_used else "Never"
            table.add_row(
                t.get("name", "—"),
                t.get("token_prefix", "—"),
                expires,
                last_used,
                status_str,
                str(t.get("id", ""))[:8] + "…",
            )

        console.print(table)

    except APIError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)


@token_app.command("revoke")
def token_revoke(
    token_id: str = typer.Argument(..., help="Token ID to revoke"),
):
    """Revoke a personal access token."""
    ensure_authenticated()

    try:
        with console.status("[cyan]Revoking token…[/cyan]"):
            api.delete(f"/tokens/{token_id}")
        console.print("[green]✓ Token revoked[/green]")
    except APIError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)


@token_app.command("login")
def token_login(
    token: str = typer.Option(..., "--token", "-t", help="Personal access token (bp-...)"),
):
    """Authenticate using a personal access token instead of email/password."""
    if not token.startswith("bp-"):
        console.print("[red]✗ Token must start with 'bp-' (personal access token)[/red]")
        raise typer.Exit(1)

    # Verify the token works
    try:
        with console.status("[cyan]Verifying token…[/cyan]"):
            resp = httpx.get(
                f"{api.base_url}/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )

        if resp.status_code != 200:
            console.print("[red]✗ Token verification failed. Check the token and try again.[/red]")
            raise typer.Exit(1)

        me = resp.json()

        # Store the PAT as the access_token in credentials
        creds = {
            "access_token": token,
            "email": me.get("email", ""),
            "user": me,
        }
        save_credentials(creds)

        # Reset HTTP client
        if api._client and not api._client.is_closed:
            api._client.close()
        api._client = None

        console.print(
            Panel(
                f"[green]✓ Authenticated via PAT as [bold]{me.get('email', '')}[/bold][/green]\n"
                f"  Organization: {me.get('org', {}).get('name', '—')}",
                title="🔑 Token Login",
                border_style="green",
            )
        )

    except httpx.RequestError as exc:
        console.print(f"[red]✗ Connection failed: {exc}[/red]")
        raise typer.Exit(1)
