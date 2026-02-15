"""Configuration management for Bonito CLI."""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from rich.console import Console

console = Console()

# Default configuration
DEFAULT_CONFIG = {
    "api_url": "https://getbonito.com",
    "default_model": None,
    "output_format": "rich",
    "auto_refresh": True,
    "timeout": 30,
}

# Configuration directories
CONFIG_DIR = Path.home() / ".bonito"
CONFIG_FILE = CONFIG_DIR / "config.json"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"


def ensure_config_dir():
    """Create config directory if it doesn't exist."""
    CONFIG_DIR.mkdir(exist_ok=True)


def load_config() -> Dict[str, Any]:
    """Load configuration from file, create defaults if missing."""
    ensure_config_dir()
    
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        # Merge with defaults for missing keys
        merged_config = DEFAULT_CONFIG.copy()
        merged_config.update(config)
        return merged_config
    
    except (json.JSONDecodeError, OSError) as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        console.print("[yellow]Using default configuration[/yellow]")
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]):
    """Save configuration to file."""
    ensure_config_dir()
    
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except OSError as e:
        console.print(f"[red]Error saving config: {e}[/red]")
        raise


def load_credentials() -> Dict[str, Any]:
    """Load credentials from file."""
    ensure_config_dir()
    
    if not CREDENTIALS_FILE.exists():
        return {}
    
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        console.print(f"[red]Error loading credentials: {e}[/red]")
        return {}


def save_credentials(credentials: Dict[str, Any]):
    """Save credentials to file."""
    ensure_config_dir()
    
    try:
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(credentials, f, indent=2)
        
        # Set restrictive permissions on credentials file
        os.chmod(CREDENTIALS_FILE, 0o600)
    except OSError as e:
        console.print(f"[red]Error saving credentials: {e}[/red]")
        raise


def clear_credentials():
    """Clear stored credentials."""
    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()


def get_api_key() -> Optional[str]:
    """Get API key from environment or credentials file."""
    # Environment variable takes precedence
    api_key = os.getenv("BONITO_API_KEY")
    if api_key:
        return api_key
    
    # Check credentials file
    creds = load_credentials()
    return creds.get("api_key") or creds.get("access_token")


def get_api_url() -> str:
    """Get API URL from environment or config."""
    # Environment variable takes precedence
    api_url = os.getenv("BONITO_API_URL")
    if api_url:
        return api_url
    
    # Check config file
    config = load_config()
    return config.get("api_url", DEFAULT_CONFIG["api_url"])


def get_config_value(key: str, default=None):
    """Get a configuration value."""
    config = load_config()
    return config.get(key, default)


def set_config_value(key: str, value: Any):
    """Set a configuration value."""
    config = load_config()
    config[key] = value
    save_config(config)


def get_refresh_token() -> Optional[str]:
    """Get refresh token from credentials."""
    creds = load_credentials()
    return creds.get("refresh_token")


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return get_api_key() is not None


def reset_config():
    """Reset configuration to defaults."""
    save_config(DEFAULT_CONFIG)
    console.print("[green]Configuration reset to defaults[/green]")


def show_config():
    """Display current configuration."""
    config = load_config()
    
    # Don't show sensitive values
    display_config = config.copy()
    if "api_key" in display_config:
        display_config["api_key"] = "***"
    
    # Add environment overrides
    if os.getenv("BONITO_API_KEY"):
        display_config["api_key"] = "*** (from env)"
    
    if os.getenv("BONITO_API_URL"):
        display_config["api_url"] = f'{os.getenv("BONITO_API_URL")} (from env)'
    
    return display_config


def get_all_config():
    """Get complete configuration including environment overrides."""
    config = load_config()
    
    # Apply environment overrides
    if os.getenv("BONITO_API_URL"):
        config["api_url"] = os.getenv("BONITO_API_URL")
    
    return config