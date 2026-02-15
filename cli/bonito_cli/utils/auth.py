"""Authentication utilities for Bonito CLI."""

from typing import Optional, Dict, Any
from datetime import datetime

import typer
from rich.console import Console

from ..config import load_credentials, save_credentials, clear_credentials, get_api_key, is_authenticated

_console = Console()


def ensure_authenticated():
    """Check auth and exit if not logged in."""
    if not is_authenticated():
        _console.print("[yellow]Not logged in. Run: bonito auth login[/yellow]")
        raise typer.Exit(1)


def validate_api_key(api_key: str) -> bool:
    """Validate API key format — accepts JWT tokens and bn- gateway keys."""
    if not api_key:
        return False
    return len(api_key) > 10


def store_auth_tokens(
    access_token: str,
    refresh_token: Optional[str] = None,
    api_key: Optional[str] = None,
    user_info: Optional[Dict] = None,
):
    """Store authentication tokens securely."""
    credentials = {
        "access_token": access_token,
        "token_type": "bearer",
        "logged_in_at": datetime.now().isoformat(),
    }
    if refresh_token:
        credentials["refresh_token"] = refresh_token
    if api_key:
        credentials["api_key"] = api_key
    if user_info:
        credentials["user"] = user_info
    save_credentials(credentials)


def logout():
    """Clear stored credentials."""
    clear_credentials()


def format_auth_status() -> str:
    """Format authentication status for display."""
    creds = load_credentials()
    if not creds.get("access_token"):
        return "Not authenticated"
    user = creds.get("user", {})
    return f"Logged in as {user.get('email', creds.get('email', 'unknown'))}"


def get_credential_summary() -> Dict[str, Any]:
    """Get a summary of stored credentials (no secrets)."""
    creds = load_credentials()
    return {
        "authenticated": bool(creds.get("access_token")),
        "email": creds.get("email", creds.get("user", {}).get("email")),
        "logged_in_at": creds.get("logged_in_at"),
    }
