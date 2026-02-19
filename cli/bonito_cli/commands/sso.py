"""SSO/SAML CLI commands.

Configure and manage SAML Single Sign-On for your organization.
"""

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.display import (
    print_success, print_error, print_info,
    format_timestamp, get_output_format
)

console = Console()
app = typer.Typer(help="🔐 SSO — SAML Single Sign-On management")


@app.command("config")
def get_config(
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Show current SSO configuration."""
    ensure_authenticated()
    fmt = get_output_format(json_output)
    
    try:
        response = api.get("/sso/config")
    except APIError as e:
        if e.status_code == 404:
            print_info("SSO not configured. Use 'bonito sso setup' to configure.")
            return
        print_error(f"Failed to fetch SSO config: {e}")
        return
    
    if fmt == "json":
        console.print_json(json.dumps(response, default=str))
        return
    
    config = response
    
    # Status indicators
    enabled_icon = "✅" if config['enabled'] else "❌"
    enforced_icon = "✅" if config['enforced'] else "❌"
    
    info_text = f"""[bold cyan]Provider Type:[/bold cyan] {config['provider_type']}
[bold cyan]Enabled:[/bold cyan] {enabled_icon} {config['enabled']}
[bold cyan]Enforced:[/bold cyan] {enforced_icon} {config['enforced']}
[bold cyan]SP Entity ID:[/bold cyan] {config.get('sp_entity_id', 'Not set')}
[bold cyan]SP ACS URL:[/bold cyan] {config.get('sp_acs_url', 'Not set')}
[bold cyan]Created:[/bold cyan] {format_timestamp(config['created_at'])}"""
    
    console.print(Panel(info_text, title="SSO Configuration"))
    
    # IdP Details
    if config.get('idp_sso_url') or config.get('idp_entity_id'):
        idp_text = ""
        if config.get('idp_sso_url'):
            idp_text += f"[bold cyan]SSO URL:[/bold cyan] {config['idp_sso_url']}\n"
        if config.get('idp_entity_id'):
            idp_text += f"[bold cyan]Entity ID:[/bold cyan] {config['idp_entity_id']}\n"
        if config.get('idp_metadata_url'):
            idp_text += f"[bold cyan]Metadata URL:[/bold cyan] {config['idp_metadata_url']}\n"
        if config.get('idp_certificate'):
            cert_preview = config['idp_certificate'][:100] + "..." if len(config['idp_certificate']) > 100 else config['idp_certificate']
            idp_text += f"[bold cyan]Certificate:[/bold cyan] {cert_preview}"
        
        if idp_text:
            console.print(Panel(idp_text.rstrip(), title="Identity Provider Details", border_style="blue"))
    
    # Mappings
    if config.get('attribute_mapping') or config.get('role_mapping'):
        mappings_text = ""
        if config.get('attribute_mapping'):
            mappings_text += "[bold]Attribute Mapping:[/bold]\n"
            mappings_text += json.dumps(config['attribute_mapping'], indent=2) + "\n\n"
        if config.get('role_mapping'):
            mappings_text += "[bold]Role Mapping:[/bold]\n"
            mappings_text += json.dumps(config['role_mapping'], indent=2)
        
        console.print(Panel(mappings_text.rstrip(), title="User Mappings", border_style="green"))
    
    # Break-glass admin
    if config.get('breakglass_user_id'):
        console.print(Panel(
            f"[bold cyan]Break-glass Admin ID:[/bold cyan] {config['breakglass_user_id']}",
            title="Emergency Access",
            border_style="red"
        ))


@app.command("setup")
def setup_sso(
    provider: str = typer.Option("custom", "--provider", "-p", help="Provider type (okta, azure_ad, google, custom)"),
    idp_sso_url: Optional[str] = typer.Option(None, "--sso-url", help="IdP Single Sign-On URL"),
    idp_entity_id: Optional[str] = typer.Option(None, "--entity-id", help="IdP Entity ID"),
    metadata_url: Optional[str] = typer.Option(None, "--metadata-url", help="IdP Metadata URL"),
    cert_file: Optional[str] = typer.Option(None, "--cert-file", help="Path to IdP certificate file"),
    interactive: bool = typer.Option(True, "--interactive/--non-interactive", help="Interactive configuration"),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
):
    """Setup or update SSO configuration."""
    ensure_authenticated()
    fmt = get_output_format(json_output)
    
    if provider not in ["okta", "azure_ad", "google", "custom"]:
        print_error("Provider must be one of: okta, azure_ad, google, custom")
        return
    
    payload = {"provider_type": provider}
    
    # Interactive setup
    if interactive:
        console.print(f"\n[bold]Setting up SAML SSO with {provider}[/bold]")
        
        if not idp_sso_url:
            idp_sso_url = Prompt.ask("IdP Single Sign-On URL")
        if not idp_entity_id:
            idp_entity_id = Prompt.ask("IdP Entity ID")
        
        if not metadata_url:
            use_metadata = Confirm.ask("Do you have an IdP metadata URL?", default=False)
            if use_metadata:
                metadata_url = Prompt.ask("IdP Metadata URL")
        
        if not cert_file and not metadata_url:
            cert_path = Prompt.ask("Path to IdP certificate file", default="")
            if cert_path:
                cert_file = cert_path
    
    # Validate required fields
    if not idp_sso_url:
        print_error("IdP SSO URL is required")
        return
    if not idp_entity_id:
        print_error("IdP Entity ID is required")
        return
    
    payload["idp_sso_url"] = idp_sso_url
    payload["idp_entity_id"] = idp_entity_id
    
    if metadata_url:
        payload["idp_metadata_url"] = metadata_url
    
    # Read certificate file
    if cert_file:
        try:
            with open(cert_file, 'r') as f:
                cert_content = f.read().strip()
                payload["idp_certificate"] = cert_content
        except FileNotFoundError:
            print_error(f"Certificate file not found: {cert_file}")
            return
    
    # Default attribute mapping
    payload["attribute_mapping"] = {
        "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
        "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname"
    }
    
    # Default role mapping
    payload["role_mapping"] = {
        "admin": ["Bonito Admins", "admin"],
        "user": ["Bonito Users", "user"]
    }
    
    try:
        response = api.put("/sso/config", data=payload)
    except APIError as e:
        print_error(f"Failed to setup SSO: {e}")
        return
    
    if fmt == "json":
        console.print_json(json.dumps(response, default=str))
        return
    
    print_success("SSO configuration saved successfully!")
    console.print(f"SP Entity ID: [cyan]{response.get('sp_entity_id')}[/cyan]")
    console.print(f"SP ACS URL: [cyan]{response.get('sp_acs_url')}[/cyan]")
    console.print("\n[yellow]⚠️  SSO is configured but not enabled. Use 'bonito sso test' then 'bonito sso enable'.[/yellow]")


@app.command("test")
def test_sso():
    """Test the SSO configuration."""
    ensure_authenticated()
    
    try:
        with console.status("[bold green]Testing SSO configuration...", spinner="dots"):
            response = api.post("/sso/test")
    except APIError as e:
        print_error(f"SSO test failed: {e}")
        return
    
    if response.get('status') == 'ok':
        print_success("SSO configuration test passed!")
        
        console.print(f"\n[bold]Test Login URL:[/bold] {response.get('test_login_url')}")
        console.print(f"[bold]SP Metadata URL:[/bold] {response.get('sp_metadata_url')}")
        console.print(f"[bold]SP Entity ID:[/bold] {response.get('sp_entity_id')}")
        console.print(f"[bold]SP ACS URL:[/bold] {response.get('sp_acs_url')}")
        
        console.print("\n[green]✨ Ready to enable SSO![/green]")
    else:
        print_error("SSO configuration test failed")
        if response.get('errors'):
            for error in response['errors']:
                console.print(f"  • {error}")


@app.command("enable")
def enable_sso():
    """Enable SSO for your organization."""
    ensure_authenticated()
    
    # Confirm
    confirmed = Confirm.ask(
        "Enable SSO? Users will be able to sign in via your IdP. "
        "Password login will still work unless you enforce SSO."
    )
    if not confirmed:
        console.print("Cancelled.")
        return
    
    try:
        response = api.post("/sso/enable")
    except APIError as e:
        print_error(f"Failed to enable SSO: {e}")
        return
    
    print_success("SSO enabled successfully!")
    console.print(response.get('message', ''))


@app.command("enforce")
def enforce_sso(
    breakglass_user_id: Optional[str] = typer.Option(None, "--breakglass-admin", help="Break-glass admin user ID"),
):
    """Enforce SSO-only authentication (disable password login)."""
    ensure_authenticated()
    
    if not breakglass_user_id:
        console.print("[yellow]⚠️  Enforcing SSO will disable password login for all users except one break-glass admin.[/yellow]")
        
        # Get current user ID as default
        try:
            me = api.get("/auth/me")
            default_admin = me.get('id')
            if me.get('role') != 'admin':
                print_error("You must be an admin to enforce SSO")
                return
        except APIError:
            default_admin = None
        
        if default_admin:
            use_me = Confirm.ask(f"Use yourself ({me.get('email')}) as break-glass admin?")
            if use_me:
                breakglass_user_id = default_admin
        
        if not breakglass_user_id:
            breakglass_user_id = Prompt.ask("Break-glass admin user ID")
    
    # Final confirmation
    console.print("\n[bold red]⚠️  WARNING: This will disable password login for all users![/bold red]")
    console.print("Only the break-glass admin will be able to use password login.")
    
    confirmed = Confirm.ask("Are you absolutely sure you want to enforce SSO-only authentication?")
    if not confirmed:
        console.print("Cancelled.")
        return
    
    payload = {"breakglass_user_id": breakglass_user_id}
    
    try:
        response = api.post("/sso/enforce", data=payload)
    except APIError as e:
        print_error(f"Failed to enforce SSO: {e}")
        return
    
    print_success("SSO enforcement enabled!")
    console.print(response.get('message', ''))
    if response.get('breakglass_admin'):
        console.print(f"Break-glass admin: [cyan]{response['breakglass_admin']}[/cyan]")


@app.command("disable")
def disable_sso():
    """Disable SSO and enforcement."""
    ensure_authenticated()
    
    confirmed = Confirm.ask(
        "Disable SSO? This will disable SSO login and enforcement. "
        "All users will need to use password login."
    )
    if not confirmed:
        console.print("Cancelled.")
        return
    
    try:
        response = api.post("/sso/disable")
    except APIError as e:
        print_error(f"Failed to disable SSO: {e}")
        return
    
    print_success("SSO disabled successfully!")
    console.print(response.get('message', ''))


@app.command("status")
def check_status(
    email: Optional[str] = typer.Option(None, "--email", help="Check SSO status for a specific email domain"),
):
    """Check SSO status for your organization or an email domain."""
    ensure_authenticated()
    
    if email:
        # Check SSO status for email domain
        payload = {"email": email}
        try:
            response = api.post("/auth/saml/check-sso", data=payload)
        except APIError as e:
            print_error(f"Failed to check SSO status: {e}")
            return
        
        if response.get('sso_enabled'):
            console.print(f"✅ SSO is [green]enabled[/green] for {email}")
            if response.get('sso_enforced'):
                console.print("🔒 SSO is [red]enforced[/red] (password login disabled)")
            console.print(f"Provider: {response.get('provider_type', 'Unknown')}")
            if response.get('sso_login_url'):
                console.print(f"Login URL: {response['sso_login_url']}")
        else:
            console.print(f"❌ SSO is [red]not enabled[/red] for {email}")
    else:
        # Show org SSO config
        try:
            config = api.get("/sso/config")
            
            status_text = f"""[bold cyan]SSO Enabled:[/bold cyan] {"✅" if config['enabled'] else "❌"} {config['enabled']}
[bold cyan]SSO Enforced:[/bold cyan] {"✅" if config['enforced'] else "❌"} {config['enforced']}
[bold cyan]Provider:[/bold cyan] {config['provider_type']}"""
            
            console.print(Panel(status_text, title="SSO Status"))
            
        except APIError as e:
            if e.status_code == 404:
                print_info("SSO not configured")
            else:
                print_error(f"Failed to check SSO status: {e}")


if __name__ == "__main__":
    app()