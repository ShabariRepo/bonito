"""Cloud provider management commands."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt

from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.display import (
    get_output_format,
    print_error,
    print_info,
    print_provider_table,
    print_success,
    print_table,
    print_warning,
)

console = Console()
app = typer.Typer(help="☁️  Cloud provider management")

_EMOJI = {
    "aws": "☁️ ", "azure": "🔷", "gcp": "🔺",
    "aws_bedrock": "☁️ ", "azure_openai": "🔷", "gcp_vertex": "🔺",
    "openai": "🤖", "anthropic": "🧠", "groq": "⚡", "openrouter": "🔀",
}


# ── list ────────────────────────────────────────────────────────


@app.command("list")
def list_providers(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all connected cloud providers."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching providers…[/cyan]"):
            providers = api.get("/providers/")

        if fmt == "json":
            import json as _json
            console.print_json(_json.dumps(providers, default=str))
        else:
            print_provider_table(providers, fmt)
            n = len(providers) if isinstance(providers, list) else 0
            if n:
                print_info(f"{n} provider(s) connected")
            else:
                print_info("No providers connected — add one with [cyan]bonito providers add aws[/cyan]")
    except APIError as exc:
        print_error(f"Failed to list providers: {exc}")


# ── status (single provider detail) ────────────────────────────


@app.command("status")
def provider_status(
    provider_id: str = typer.Argument(..., help="Provider UUID"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Show detailed status for a single provider."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Fetching provider…[/cyan]"):
            detail = api.get(f"/providers/{provider_id}/summary")

        if fmt == "json":
            import json as _json
            console.print_json(_json.dumps(detail, default=str))
        else:
            from ..utils.display import print_dict_as_table
            info = {
                "Name": detail.get("name", "—"),
                "Type": detail.get("type", "—"),
                "Status": detail.get("status", "—"),
                "Region": detail.get("config", {}).get("region", "—"),
                "Models": detail.get("model_count", "—"),
                "Created": detail.get("created_at", "—"),
            }
            print_dict_as_table(info, title=f"{_EMOJI.get(detail.get('type',''), '☁️ ')} Provider Detail")
    except APIError as exc:
        print_error(f"Failed to get provider status: {exc}")


# ── add (sub-group) ────────────────────────────────────────────

add_app = typer.Typer(help="Connect a new cloud provider", no_args_is_help=True)


def _connect_provider(provider_data: dict, fmt: str, label: str):
    """Helper to POST /providers/connect and test."""
    try:
        with console.status(f"[cyan]Connecting {label}…[/cyan]"):
            result = api.post("/providers/connect", provider_data)

        if fmt == "json":
            import json as _json
            console.print_json(_json.dumps(result, default=str))
        else:
            print_success(f"{label} connected successfully")
            pid = result.get("id")
            if pid:
                try:
                    api.post(f"/providers/{pid}/verify")
                    print_success("Connection test passed")
                except Exception:
                    print_warning("Could not verify connection — check credentials")
    except APIError as exc:
        print_error(f"Failed to connect {label}: {exc}")


@add_app.command("aws")
def add_aws(
    access_key: Optional[str] = typer.Option(None, "--access-key", help="AWS Access Key ID"),
    secret_key: Optional[str] = typer.Option(None, "--secret-key", help="AWS Secret Access Key"),
    region: str = typer.Option("us-east-1", "--region", help="AWS region"),
    name: Optional[str] = typer.Option(None, "--name", help="Display name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Connect an AWS Bedrock provider."""
    ensure_authenticated()
    if not access_key:
        access_key = Prompt.ask("AWS Access Key ID", password=True)
    if not secret_key:
        secret_key = Prompt.ask("AWS Secret Access Key", password=True)
    _connect_provider(
        {
            "provider_type": "aws",
            "name": name or f"AWS Bedrock ({region})",
            "credentials": {"access_key_id": access_key, "secret_access_key": secret_key, "region": region},
        },
        get_output_format(json_output),
        "AWS Bedrock",
    )


@add_app.command("azure")
def add_azure(
    tenant_id: Optional[str] = typer.Option(None, "--tenant-id"),
    client_id: Optional[str] = typer.Option(None, "--client-id"),
    client_secret: Optional[str] = typer.Option(None, "--client-secret"),
    subscription_id: Optional[str] = typer.Option(None, "--subscription-id"),
    endpoint: Optional[str] = typer.Option(None, "--endpoint"),
    region: str = typer.Option("eastus", "--region"),
    name: Optional[str] = typer.Option(None, "--name"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Connect an Azure OpenAI provider."""
    ensure_authenticated()
    if not tenant_id:
        tenant_id = Prompt.ask("Azure Tenant ID")
    if not client_id:
        client_id = Prompt.ask("Azure Client ID")
    if not client_secret:
        client_secret = Prompt.ask("Azure Client Secret", password=True)
    if not subscription_id:
        subscription_id = Prompt.ask("Azure Subscription ID")
    if not endpoint:
        endpoint = Prompt.ask("Azure OpenAI Endpoint URL")

    _connect_provider(
        {
            "provider_type": "azure",
            "name": name or f"Azure OpenAI ({region})",
            "credentials": {
                "tenant_id": tenant_id,
                "client_id": client_id,
                "client_secret": client_secret,
                "subscription_id": subscription_id,
                "endpoint": endpoint,
                "azure_mode": "openai",
            },
        },
        get_output_format(json_output),
        "Azure OpenAI",
    )


@add_app.command("gcp")
def add_gcp(
    project_id: Optional[str] = typer.Option(None, "--project-id"),
    service_account_json: Optional[str] = typer.Option(None, "--service-account-json", help="Path to JSON file"),
    region: str = typer.Option("us-central1", "--region"),
    name: Optional[str] = typer.Option(None, "--name"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Connect a Google Vertex AI provider."""
    ensure_authenticated()
    if not project_id:
        project_id = Prompt.ask("GCP Project ID")
    if not service_account_json:
        service_account_json = Prompt.ask("Path to service account JSON")
    try:
        with open(service_account_json) as fh:
            sa_data = fh.read()
    except Exception as exc:
        print_error(f"Cannot read service account file: {exc}")
        return

    _connect_provider(
        {
            "provider_type": "gcp",
            "name": name or f"Google Vertex AI ({region})",
            "credentials": {"project_id": project_id, "service_account_json": sa_data, "region": region},
        },
        get_output_format(json_output),
        "Google Vertex AI",
    )


@add_app.command("openai")
def add_openai(
    api_key: Optional[str] = typer.Option(None, "--api-key", help="OpenAI API key"),
    name: Optional[str] = typer.Option(None, "--name"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Connect an OpenAI provider."""
    ensure_authenticated()
    if not api_key:
        api_key = Prompt.ask("OpenAI API Key", password=True)
    _connect_provider(
        {"provider_type": "openai", "name": name or "OpenAI", "credentials": {"api_key": api_key}},
        get_output_format(json_output),
        "OpenAI",
    )


@add_app.command("anthropic")
def add_anthropic(
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Anthropic API key"),
    name: Optional[str] = typer.Option(None, "--name"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Connect an Anthropic provider."""
    ensure_authenticated()
    if not api_key:
        api_key = Prompt.ask("Anthropic API Key", password=True)
    _connect_provider(
        {"provider_type": "anthropic", "name": name or "Anthropic", "credentials": {"api_key": api_key}},
        get_output_format(json_output),
        "Anthropic",
    )


@add_app.command("groq")
def add_groq(
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Groq API key"),
    name: Optional[str] = typer.Option(None, "--name"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Connect a Groq provider."""
    ensure_authenticated()
    if not api_key:
        api_key = Prompt.ask("Groq API Key", password=True)
    _connect_provider(
        {"provider_type": "groq", "name": name or "Groq", "credentials": {"api_key": api_key}},
        get_output_format(json_output),
        "Groq",
    )


@add_app.command("openrouter")
def add_openrouter(
    api_key: Optional[str] = typer.Option(None, "--api-key", help="OpenRouter API key"),
    name: Optional[str] = typer.Option(None, "--name"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Connect an OpenRouter provider."""
    ensure_authenticated()
    if not api_key:
        api_key = Prompt.ask("OpenRouter API Key", password=True)
    _connect_provider(
        {"provider_type": "openrouter", "name": name or "OpenRouter", "credentials": {"api_key": api_key}},
        get_output_format(json_output),
        "OpenRouter",
    )


app.add_typer(add_app, name="add")


# ── test ────────────────────────────────────────────────────────


@app.command("test")
def test_provider(
    provider_id: str = typer.Argument(..., help="Provider UUID to test"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Test provider credentials and connectivity."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    try:
        with console.status("[cyan]Testing provider…[/cyan]"):
            result = api.post(f"/providers/{provider_id}/verify")

        if fmt == "json":
            import json as _json
            console.print_json(_json.dumps(result, default=str))
        else:
            if result.get("status") == "success":
                print_success("Provider test passed ✓")
            else:
                print_warning(f"Provider test returned: {result.get('status', 'unknown')}")
    except APIError as exc:
        print_error(f"Provider test failed: {exc}")


# ── remove ──────────────────────────────────────────────────────


@app.command("remove")
def remove_provider(
    provider_id: str = typer.Argument(..., help="Provider UUID to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Disconnect and remove a cloud provider."""
    fmt = get_output_format(json_output)
    ensure_authenticated()

    if not force and fmt != "json":
        if not typer.confirm(f"Remove provider {provider_id[:8]}…?"):
            print_info("Cancelled")
            return

    try:
        api.delete(f"/providers/{provider_id}")
        if fmt == "json":
            console.print_json(f'{{"status":"deleted","id":"{provider_id}"}}')
        else:
            print_success(f"Provider {provider_id[:8]}… removed")
    except APIError as exc:
        print_error(f"Failed to remove provider: {exc}")
