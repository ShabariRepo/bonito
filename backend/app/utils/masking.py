"""Credential masking utilities — NEVER return full credentials in API responses."""


def mask_value(value: str, visible_chars: int = 4) -> str:
    """Show first 4 + last 4 chars, mask middle. For short values, mask more aggressively."""
    if not value or len(value) <= visible_chars * 2:
        return "••••••••"
    return f"{value[:visible_chars]}****{value[-visible_chars:]}"


def mask_secret(value: str | None) -> str:
    """Fully mask a secret value — never show any characters."""
    return "••••••••" if value else ""


def mask_credentials(provider_type: str, credentials: dict) -> dict:
    """Return a masked version of credentials suitable for API responses.

    Rules:
    - IDs/keys that identify (not authenticate): show first 4 + last 4
    - Secrets/passwords: fully masked
    - Regions/projects: show in full (not sensitive)
    """
    if not credentials:
        return {}

    if provider_type == "aws":
        return {
            "access_key_id": mask_value(credentials.get("access_key_id", "")),
            "secret_access_key": mask_secret(credentials.get("secret_access_key")),
            "region": credentials.get("region", "us-east-1"),
        }
    elif provider_type == "azure":
        return {
            "tenant_id": mask_value(credentials.get("tenant_id", "")),
            "client_id": mask_value(credentials.get("client_id", "")),
            "client_secret": mask_secret(credentials.get("client_secret")),
            "subscription_id": mask_value(credentials.get("subscription_id", "")),
            "resource_group": credentials.get("resource_group", ""),
            "endpoint": credentials.get("endpoint", ""),
        }
    elif provider_type == "gcp":
        return {
            "project_id": credentials.get("project_id", ""),
            "service_account_json": mask_secret(credentials.get("service_account_json")),
            "region": credentials.get("region", "us-central1"),
        }
    return {}
