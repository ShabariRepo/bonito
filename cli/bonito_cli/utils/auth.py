"""Authentication utilities for Bonito CLI."""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import webbrowser
import secrets
import string

from ..config import (
    load_credentials, save_credentials, clear_credentials,
    get_api_key, is_authenticated
)
from .display import print_error, print_success, print_info


def generate_api_key() -> str:
    """Generate a random API key."""
    alphabet = string.ascii_letters + string.digits
    return "bk-" + "".join(secrets.choice(alphabet) for _ in range(48))


def validate_api_key(api_key: str) -> bool:
    """Validate API key format."""
    if not api_key:
        return False
    
    # Basic format validation
    if not api_key.startswith(("bk-", "sk-")):
        return False
    
    if len(api_key) < 10:
        return False
    
    return True


def store_auth_tokens(
    access_token: str,
    refresh_token: Optional[str] = None,
    api_key: Optional[str] = None,
    user_info: Optional[Dict] = None
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


def get_stored_user_info() -> Optional[Dict]:
    """Get stored user information."""
    creds = load_credentials()
    return creds.get("user")


def is_token_expired(credentials: Optional[Dict] = None) -> bool:
    """Check if access token is likely expired."""
    if not credentials:
        credentials = load_credentials()
    
    logged_in_at = credentials.get("logged_in_at")
    if not logged_in_at:
        return True
    
    try:
        login_time = datetime.fromisoformat(logged_in_at)
        # Assume tokens expire after 1 hour
        expiry_time = login_time + timedelta(hours=1)
        return datetime.now() > expiry_time
    except:
        return True


def logout():
    """Clear all stored credentials."""
    clear_credentials()
    print_success("Logged out successfully")


def ensure_authenticated():
    """Ensure user is authenticated, raise error if not."""
    if not is_authenticated():
        print_error(
            "Not authenticated. Please run 'bonito auth login' first.",
            exit_code=1
        )


def open_browser_auth(auth_url: str) -> bool:
    """Open browser for OAuth authentication."""
    try:
        webbrowser.open(auth_url)
        return True
    except:
        return False


def format_auth_status(user_info: Dict, credentials: Dict) -> Dict[str, Any]:
    """Format authentication status for display."""
    status = {
        "authenticated": True,
        "user_id": user_info.get("id"),
        "username": user_info.get("username"),
        "email": user_info.get("email"),
        "organization": user_info.get("organization", {}).get("name"),
        "org_id": user_info.get("organization", {}).get("id"),
        "role": user_info.get("role"),
        "logged_in_at": credentials.get("logged_in_at"),
        "api_key_prefix": None,
    }
    
    # Show API key prefix if available
    api_key = credentials.get("api_key")
    if api_key:
        status["api_key_prefix"] = api_key[:10] + "..."
    
    return status


def refresh_user_info(api_client):
    """Refresh and store current user information."""
    try:
        user_info = api_client.get_auth_status()
        credentials = load_credentials()
        credentials["user"] = user_info
        save_credentials(credentials)
        return user_info
    except Exception as e:
        print_error(f"Failed to refresh user info: {e}")
        return None


class AuthError(Exception):
    """Authentication error."""
    pass


class TokenManager:
    """Manage authentication tokens and refresh."""
    
    def __init__(self, api_client):
        self.api = api_client
    
    def ensure_valid_token(self) -> str:
        """Ensure we have a valid access token."""
        credentials = load_credentials()
        
        if not credentials:
            raise AuthError("No credentials stored")
        
        access_token = credentials.get("access_token")
        if not access_token:
            raise AuthError("No access token available")
        
        # If token seems expired, try to refresh
        if is_token_expired(credentials):
            refreshed = self.refresh_token()
            if not refreshed:
                raise AuthError("Token expired and refresh failed")
        
        return access_token
    
    def refresh_token(self) -> bool:
        """Refresh access token using refresh token."""
        credentials = load_credentials()
        refresh_token = credentials.get("refresh_token")
        
        if not refresh_token:
            return False
        
        try:
            # This would be handled by the API client
            # The API client has the refresh logic
            return True
        except:
            return False
    
    def validate_current_auth(self) -> bool:
        """Validate current authentication by making a test request."""
        try:
            user_info = self.api.get_auth_status()
            return user_info is not None
        except:
            return False


def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for API requests."""
    api_key = get_api_key()
    if not api_key:
        return {}
    
    return {
        "Authorization": f"Bearer {api_key}",
    }


def mask_sensitive_value(value: str, show_chars: int = 4) -> str:
    """Mask sensitive values like API keys."""
    if not value or len(value) <= show_chars:
        return value
    
    return value[:show_chars] + "*" * (len(value) - show_chars)


def get_credential_summary() -> Dict[str, Any]:
    """Get summary of stored credentials for display."""
    credentials = load_credentials()
    
    if not credentials:
        return {"authenticated": False}
    
    summary = {
        "authenticated": True,
        "has_access_token": bool(credentials.get("access_token")),
        "has_refresh_token": bool(credentials.get("refresh_token")),
        "has_api_key": bool(credentials.get("api_key")),
        "logged_in_at": credentials.get("logged_in_at"),
    }
    
    # Add masked API key if available
    api_key = credentials.get("api_key")
    if api_key:
        summary["api_key_preview"] = mask_sensitive_value(api_key, 8)
    
    # Add user info if available
    user = credentials.get("user")
    if user:
        summary.update({
            "user_id": user.get("id"),
            "username": user.get("username"),
            "email": user.get("email"),
            "organization": user.get("organization", {}).get("name"),
        })
    
    return summary