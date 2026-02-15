"""Authentication commands for Bonito CLI."""

import typer
from rich.console import Console
from rich.prompt import Prompt
from typing import Optional

from ..api import api, APIError
from ..config import clear_credentials, is_authenticated
from ..utils.display import (
    print_error, print_success, print_info, print_table,
    print_dict_as_table, get_output_format
)
from ..utils.auth import (
    validate_api_key, store_auth_tokens, logout,
    format_auth_status, get_credential_summary
)

console = Console()

app = typer.Typer(help="🔐 Authentication & API key management")


@app.command("login")
def login(
    api_key: Optional[str] = typer.Option(
        None, 
        "--api-key", 
        help="API key for direct authentication"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Authenticate with Bonito API.
    
    You can either provide an API key directly or use interactive authentication.
    Get your API key from https://getbonito.com/dashboard/api-keys
    """
    output_format = get_output_format(json_output)
    
    # If no API key provided, prompt for it
    if not api_key:
        print_info("Get your API key from: https://getbonito.com/dashboard/api-keys")
        api_key = Prompt.ask(
            "\n[cyan]Enter your API key[/cyan]",
            password=True
        )
    
    if not api_key:
        print_error("API key is required")
        return
    
    # Validate API key format
    if not validate_api_key(api_key):
        print_error("Invalid API key format. API keys should start with 'bk-' or 'sk-'")
        return
    
    try:
        # Attempt login
        response = api.login(api_key)
        
        # Get user info
        user_info = api.get_auth_status()
        
        # Store credentials
        store_auth_tokens(
            access_token=response.get("access_token", api_key),
            refresh_token=response.get("refresh_token"),
            api_key=api_key,
            user_info=user_info
        )
        
        if output_format == "json":
            login_info = {
                "status": "success",
                "message": "Logged in successfully",
                "user": user_info
            }
            console.print_json(login_info)
        else:
            print_success("Logged in successfully!")
            
            # Show user info
            org_name = user_info.get("organization", {}).get("name", "Personal")
            console.print(f"✨ Welcome [cyan]{user_info.get('username', 'User')}[/cyan]")
            console.print(f"📊 Organization: [yellow]{org_name}[/yellow]")
            
            print_info("You can now use all Bonito CLI commands")
            print_info("Try: bonito models list")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({
                "status": "error",
                "message": str(e),
                "code": e.status_code
            })
        else:
            print_error(f"Login failed: {e}")


@app.command("logout")
def logout_cmd(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Clear stored credentials and log out.
    """
    output_format = get_output_format(json_output)
    
    if not is_authenticated():
        if output_format == "json":
            console.print_json({"status": "info", "message": "Not logged in"})
        else:
            print_info("Already logged out")
        return
    
    logout()
    
    if output_format == "json":
        console.print_json({"status": "success", "message": "Logged out successfully"})
    else:
        print_success("Logged out successfully")


@app.command("status")
def status(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Show current authentication status and user information.
    """
    output_format = get_output_format(json_output)
    
    if not is_authenticated():
        if output_format == "json":
            console.print_json({
                "authenticated": False,
                "message": "Not logged in"
            })
        else:
            print_error("Not authenticated. Run 'bonito auth login' first.", exit_code=0)
        return
    
    try:
        # Get current user info
        user_info = api.get_auth_status()
        credentials = get_credential_summary()
        
        status_info = format_auth_status(user_info, credentials)
        
        if output_format == "json":
            console.print_json(status_info)
        else:
            # Rich display
            console.print("\n[bold green]✅ Authenticated[/bold green]")
            
            user_table = {
                "Username": user_info.get("username", "N/A"),
                "Email": user_info.get("email", "N/A"),
                "User ID": user_info.get("id", "N/A"),
                "Role": user_info.get("role", "user").title(),
            }
            
            org_info = user_info.get("organization", {})
            if org_info:
                user_table.update({
                    "Organization": org_info.get("name", "N/A"),
                    "Org ID": org_info.get("id", "N/A"),
                })
            
            print_dict_as_table(user_table, title="User Information")
            
            # Show credential info
            cred_info = {
                "Logged in": credentials.get("logged_in_at", "N/A"),
                "API Key": credentials.get("api_key_preview", "N/A"),
            }
            print_dict_as_table(cred_info, title="Credentials")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({
                "authenticated": False,
                "error": str(e)
            })
        else:
            print_error(f"Failed to get auth status: {e}")


@app.command("keys")
def keys_command():
    """
    API key management commands.
    
    Use subcommands:
    - bonito auth keys list
    - bonito auth keys create
    - bonito auth keys revoke
    """
    print_info("Use subcommands: list, create, revoke")
    console.print("Try: [cyan]bonito auth keys list[/cyan]")


# Gateway keys subcommands
keys_app = typer.Typer(help="API key management", no_args_is_help=True)


@keys_app.command("list")
def list_keys(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """List all gateway API keys."""
    output_format = get_output_format(json_output)
    
    if not is_authenticated():
        print_error("Not authenticated. Run 'bonito auth login' first.")
        return
    
    try:
        keys = api.get_gateway_keys()
        
        if output_format == "json":
            console.print_json(keys)
        else:
            if not keys:
                print_info("No API keys found")
                print_info("Create one with: bonito auth keys create")
                return
            
            # Format keys for display
            key_data = []
            for key in keys:
                key_data.append({
                    "ID": key.get("id", ""),
                    "Name": key.get("name", "Unnamed"),
                    "Key Preview": key.get("key", "")[:12] + "...",
                    "Created": key.get("created_at", ""),
                    "Status": "Active" if key.get("active", True) else "Inactive",
                    "Last Used": key.get("last_used_at", "Never"),
                })
            
            print_table(key_data, title="Gateway API Keys")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to list keys: {e}")


@keys_app.command("create")
def create_key(
    name: Optional[str] = typer.Option(None, "--name", help="Name for the API key"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Create a new gateway API key."""
    output_format = get_output_format(json_output)
    
    if not is_authenticated():
        print_error("Not authenticated. Run 'bonito auth login' first.")
        return
    
    # Prompt for name if not provided
    if not name:
        name = Prompt.ask("Enter a name for this API key", default="CLI Key")
    
    try:
        key_info = api.create_gateway_key(name)
        
        if output_format == "json":
            console.print_json(key_info)
        else:
            print_success(f"API key created: {name}")
            
            console.print(f"\n[bold yellow]⚠️  API Key (save this, it won't be shown again):[/bold yellow]")
            console.print(f"[green]{key_info.get('key', '')}[/green]")
            
            console.print(f"\n[bold]Key ID:[/bold] {key_info.get('id', '')}")
            console.print(f"[bold]Name:[/bold] {key_info.get('name', '')}")
            
            print_info("Use this key to authenticate with the Bonito Gateway API")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to create key: {e}")


@keys_app.command("revoke")
def revoke_key(
    key_id: str = typer.Argument(..., help="API key ID to revoke"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """Revoke a gateway API key."""
    output_format = get_output_format(json_output)
    
    if not is_authenticated():
        print_error("Not authenticated. Run 'bonito auth login' first.")
        return
    
    # Confirm revocation
    if output_format == "rich":
        confirm = typer.confirm(f"Are you sure you want to revoke key {key_id}?")
        if not confirm:
            print_info("Cancelled")
            return
    
    try:
        api.revoke_gateway_key(key_id)
        
        if output_format == "json":
            console.print_json({
                "status": "success", 
                "message": f"Key {key_id} revoked"
            })
        else:
            print_success(f"API key {key_id} revoked")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to revoke key: {e}")


# Add keys subcommand to main auth app
app.add_typer(keys_app, name="keys")


if __name__ == "__main__":
    app()