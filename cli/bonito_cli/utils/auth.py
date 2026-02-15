"""Authentication utilities for Bonito CLI."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..config import (
    clear_credentials,
    get_api_key,
    is_authenticated,
    load_credentials,
    save_credentials,
)
from .display import print_error


def ensure_authenticated() -> None:
    """Abort with a helpful message if the user is not logged in."""
    if not is_authenticated():
        print_error("Not authenticated. Run [cyan]bonito auth login[/cyan] first.", exit_code=1)


def mask_value(value: str, show: int = 4) -> str:
    """Mask a sensitive string, keeping the first *show* characters."""
    if not value or len(value) <= show:
        return value
    return value[:show] + "•" * min(len(value) - show, 20)


def get_credential_summary() -> Dict[str, Any]:
    """Return a safe-to-display summary of stored credentials."""
    creds = load_credentials()
    if not creds:
        return {"authenticated": False}

    summary: Dict[str, Any] = {
        "authenticated": True,
        "has_access_token": bool(creds.get("access_token")),
        "has_refresh_token": bool(creds.get("refresh_token")),
        "email": creds.get("email"),
    }

    user = creds.get("user")
    if user:
        summary["name"] = user.get("name")
        summary["role"] = user.get("role")
        summary["org"] = user.get("org", {}).get("name")

    return summary
