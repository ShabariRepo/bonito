"""Onboarding wizard API endpoints.

GET  /api/onboarding/progress       — Get org's onboarding state
PUT  /api/onboarding/progress       — Update onboarding state
POST /api/onboarding/generate-iac   — Generate IaC code for provider+tool
GET  /api/onboarding/download-iac   — Download IaC files as ZIP
POST /api/onboarding/validate       — Validate pasted credentials
"""

import io
import time
import uuid
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.onboarding import OnboardingProgress
from app.schemas.onboarding import (
    ConnectionHealth,
    OnboardingProgressResponse,
    OnboardingProgressUpdate,
    GenerateIaCRequest,
    GenerateIaCResponse,
    ValidateCredentialsRequest,
    ValidateCredentialsResponse,
)
from app.services.iac_templates import generate_iac

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

TOTAL_STEPS = 5

# Valid combinations: which tools work with which providers
VALID_COMBOS = {
    "aws": {"terraform", "pulumi", "cloudformation", "manual"},
    "azure": {"terraform", "pulumi", "bicep", "manual"},
    "gcp": {"terraform", "pulumi", "manual"},
}


def _completion_pct(progress: OnboardingProgress) -> int:
    if progress.completed:
        return 100
    # Steps 1-5, each worth 20%
    return min(int((progress.current_step - 1) / TOTAL_STEPS * 100), 100)


def _to_response(p: OnboardingProgress) -> OnboardingProgressResponse:
    return OnboardingProgressResponse(
        id=p.id,
        org_id=p.org_id,
        current_step=p.current_step,
        completed=p.completed,
        completion_percentage=_completion_pct(p),
        selected_providers=p.selected_providers,
        selected_iac_tool=p.selected_iac_tool,
        provider_credentials_validated=p.provider_credentials_validated,
        step_timestamps=p.step_timestamps,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.get("/progress", response_model=OnboardingProgressResponse)
async def get_progress(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current org's onboarding progress. Creates a new record if none exists."""
    result = await db.execute(
        select(OnboardingProgress).where(OnboardingProgress.org_id == user.org_id)
    )
    progress = result.scalar_one_or_none()

    if not progress:
        progress = OnboardingProgress(
            id=uuid.uuid4(),
            org_id=user.org_id,
            current_step=1,
            completed=False,
            step_timestamps={"1": datetime.now(timezone.utc).isoformat()},
        )
        db.add(progress)
        await db.flush()

    return _to_response(progress)


@router.put("/progress", response_model=OnboardingProgressResponse)
async def update_progress(
    body: OnboardingProgressUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update onboarding progress. Saves state so users can resume."""
    result = await db.execute(
        select(OnboardingProgress).where(OnboardingProgress.org_id == user.org_id)
    )
    progress = result.scalar_one_or_none()

    if not progress:
        progress = OnboardingProgress(
            id=uuid.uuid4(),
            org_id=user.org_id,
            current_step=1,
            completed=False,
            step_timestamps={},
        )
        db.add(progress)

    if body.current_step is not None:
        progress.current_step = body.current_step
        ts = progress.step_timestamps or {}
        ts[str(body.current_step)] = datetime.now(timezone.utc).isoformat()
        progress.step_timestamps = ts

    if body.selected_providers is not None:
        for p in body.selected_providers:
            if p not in VALID_COMBOS:
                raise HTTPException(400, f"Invalid provider: {p}. Must be: {list(VALID_COMBOS.keys())}")
        progress.selected_providers = body.selected_providers

    if body.selected_iac_tool is not None:
        progress.selected_iac_tool = body.selected_iac_tool

    if body.provider_credentials_validated is not None:
        progress.provider_credentials_validated = body.provider_credentials_validated

    if body.completed is not None:
        progress.completed = body.completed

    progress.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return _to_response(progress)


@router.post("/generate-iac", response_model=GenerateIaCResponse)
async def generate_iac_code(
    body: GenerateIaCRequest,
):
    """Generate IaC code for a provider+tool combination."""
    valid_tools = VALID_COMBOS.get(body.provider, set())
    if body.iac_tool not in valid_tools:
        raise HTTPException(
            400,
            f"{body.provider} does not support {body.iac_tool}. "
            f"Valid tools: {sorted(valid_tools)}",
        )

    try:
        result = generate_iac(
            provider=body.provider,
            iac_tool=body.iac_tool,
            project_name=body.project_name or "bonito",
            region=body.region,
            aws_account_id=body.aws_account_id,
            azure_subscription_id=body.azure_subscription_id,
            gcp_project_id=body.gcp_project_id,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return GenerateIaCResponse(
        provider=body.provider,
        iac_tool=body.iac_tool,
        code=result["code"],
        filename=result["filename"],
        files=[{"filename": f["filename"], "content": f["content"]} for f in result.get("files", [])],
        instructions=result["instructions"],
        security_notes=result["security_notes"],
    )


@router.get("/download-iac")
async def download_iac_zip(
    provider: str = Query(..., pattern="^(aws|azure|gcp)$"),
    tool: str = Query(default="terraform", pattern="^(terraform|pulumi|cloudformation|bicep|manual)$"),
):
    """Download IaC template files as a ZIP archive.

    GET /api/onboarding/download-iac?provider=aws&tool=terraform
    """
    valid_tools = VALID_COMBOS.get(provider, set())
    if tool not in valid_tools:
        raise HTTPException(
            400,
            f"{provider} does not support {tool}. Valid tools: {sorted(valid_tools)}",
        )

    try:
        result = generate_iac(provider=provider, iac_tool=tool)
    except ValueError as e:
        raise HTTPException(400, str(e))

    files = result.get("files", [])
    if not files:
        raise HTTPException(404, "No files available for this combination")

    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    dir_name = f"bonito-{provider}-{tool}"
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.writestr(f"{dir_name}/{f['filename']}", f["content"])

        # Add a README with instructions and security notes
        readme = f"# Bonito {provider.upper()} — {tool.title()} Setup\n\n"
        readme += "## Instructions\n\n"
        for i, inst in enumerate(result.get("instructions", []), 1):
            readme += f"{i}. {inst}\n"
        readme += "\n## Security Notes\n\n"
        for note in result.get("security_notes", []):
            readme += f"- {note}\n"
        zf.writestr(f"{dir_name}/README.md", readme)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{dir_name}.zip"',
        },
    )


@router.post("/validate", response_model=ValidateCredentialsResponse)
async def validate_credentials(
    body: ValidateCredentialsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Validate pasted credentials by calling the provider's validation endpoint.

    Delegates to the existing provider validation services.
    Returns health status on successful validation.
    """
    provider = body.provider
    creds = body.credentials

    try:
        if provider == "aws":
            identity, permissions, errors, health_checks = await _validate_aws(creds)
        elif provider == "azure":
            identity, permissions, errors, health_checks = await _validate_azure(creds)
        elif provider == "gcp":
            identity, permissions, errors, health_checks = await _validate_gcp(creds)
        else:
            raise HTTPException(400, f"Unknown provider: {provider}")
    except HTTPException:
        raise
    except Exception as e:
        return ValidateCredentialsResponse(
            provider=provider,
            valid=False,
            errors=[str(e)],
        )

    valid = len(errors) == 0

    # Build health status
    health = None
    if valid:
        all_healthy = all(c.get("status") == "healthy" for c in health_checks)
        any_error = any(c.get("status") == "error" for c in health_checks)
        health = ConnectionHealth(
            provider=provider,
            status="healthy" if all_healthy else ("error" if any_error else "degraded"),
            checks=health_checks,
            checked_at=datetime.now(timezone.utc),
        )

    # Update onboarding progress if valid (skip if no auth context)
    # Progress tracking requires auth — silently skip for unauthenticated onboarding

    return ValidateCredentialsResponse(
        provider=provider,
        valid=valid,
        identity=identity,
        permissions=permissions if valid else None,
        errors=errors if errors else None,
        health=health,
    )


async def _validate_aws(creds: dict) -> tuple[str | None, list[str] | None, list[str], list[dict]]:
    """Validate AWS credentials using STS get-caller-identity."""
    errors = []
    health_checks = []
    access_key = creds.get("access_key_id")
    secret_key = creds.get("secret_access_key")
    role_arn = creds.get("role_arn")
    region = creds.get("region", "us-east-1")

    if not access_key or not secret_key:
        return None, None, ["Missing access_key_id or secret_access_key"], []

    try:
        import boto3
        start = time.monotonic()
        sts = boto3.client(
            "sts",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        identity = sts.get_caller_identity()
        arn = identity.get("Arn", "unknown")
        latency = int((time.monotonic() - start) * 1000)

        health_checks.append({
            "name": "STS Authentication",
            "status": "healthy",
            "message": f"Authenticated as {arn} ({latency}ms)",
        })

        permissions = []

        # If role_arn provided, try assuming it
        if role_arn:
            try:
                start = time.monotonic()
                assumed = sts.assume_role(
                    RoleArn=role_arn,
                    RoleSessionName="bonito-validation",
                    ExternalId="bonito-external-id",
                )
                latency = int((time.monotonic() - start) * 1000)
                permissions.append("sts:AssumeRole ✅")
                health_checks.append({
                    "name": "Role Assumption",
                    "status": "healthy",
                    "message": f"Successfully assumed {role_arn} ({latency}ms)",
                })

                # Use assumed role credentials for further checks
                assumed_creds = assumed["Credentials"]
                bedrock = boto3.client(
                    "bedrock",
                    aws_access_key_id=assumed_creds["AccessKeyId"],
                    aws_secret_access_key=assumed_creds["SecretAccessKey"],
                    aws_session_token=assumed_creds["SessionToken"],
                    region_name=region,
                )
                ce = boto3.client(
                    "ce",
                    aws_access_key_id=assumed_creds["AccessKeyId"],
                    aws_secret_access_key=assumed_creds["SecretAccessKey"],
                    aws_session_token=assumed_creds["SessionToken"],
                    region_name=region,
                )
            except Exception as e:
                permissions.append("sts:AssumeRole ❌")
                errors.append(f"Cannot assume role {role_arn}: {e}")
                health_checks.append({
                    "name": "Role Assumption",
                    "status": "error",
                    "message": str(e),
                })
                return arn, permissions, errors, health_checks
        else:
            bedrock = boto3.client(
                "bedrock",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
            )
            ce = boto3.client(
                "ce",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
            )

        # Check Bedrock access
        try:
            start = time.monotonic()
            bedrock.list_foundation_models()
            latency = int((time.monotonic() - start) * 1000)
            permissions.append("bedrock:ListFoundationModels ✅")
            health_checks.append({
                "name": "Bedrock Access",
                "status": "healthy",
                "message": f"Can list foundation models ({latency}ms)",
            })
        except Exception as e:
            permissions.append("bedrock:ListFoundationModels ❌")
            errors.append("Cannot list Bedrock models — check IAM policy")
            health_checks.append({
                "name": "Bedrock Access",
                "status": "error",
                "message": str(e),
            })

        # Check Cost Explorer
        try:
            start = time.monotonic()
            ce.get_cost_and_usage(
                TimePeriod={"Start": "2026-01-01", "End": "2026-01-02"},
                Granularity="DAILY",
                Metrics=["BlendedCost"],
            )
            latency = int((time.monotonic() - start) * 1000)
            permissions.append("ce:GetCostAndUsage ✅")
            health_checks.append({
                "name": "Cost Explorer",
                "status": "healthy",
                "message": f"Can read cost data ({latency}ms)",
            })
        except Exception:
            permissions.append("ce:GetCostAndUsage ❌")
            health_checks.append({
                "name": "Cost Explorer",
                "status": "degraded",
                "message": "Cannot read cost data (optional — dashboards may be limited)",
            })

        return arn, permissions, errors, health_checks

    except ImportError:
        return None, None, ["boto3 not installed — cannot validate AWS credentials"], []
    except Exception as e:
        return None, None, [f"AWS credential validation failed: {str(e)}"], []


async def _validate_azure(creds: dict) -> tuple[str | None, list[str] | None, list[str], list[dict]]:
    """Validate Azure credentials using OAuth2 client credentials flow."""
    errors = []
    health_checks = []
    tenant_id = creds.get("tenant_id")
    client_id = creds.get("client_id")
    client_secret = creds.get("client_secret")
    subscription_id = creds.get("subscription_id")
    resource_group_name = creds.get("resource_group_name")

    if not all([tenant_id, client_id, client_secret, subscription_id]):
        return None, None, ["Missing tenant_id, client_id, client_secret, or subscription_id"], []

    try:
        import httpx

        # Get OAuth token
        async with httpx.AsyncClient() as client:
            start = time.monotonic()
            token_resp = await client.post(
                f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": "https://management.azure.com/.default",
                },
            )
            latency = int((time.monotonic() - start) * 1000)

            if token_resp.status_code != 200:
                return None, None, ["Azure authentication failed — check tenant_id, client_id, client_secret"], []

            health_checks.append({
                "name": "OAuth Authentication",
                "status": "healthy",
                "message": f"Token acquired ({latency}ms)",
            })

            token = token_resp.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            permissions = []

            # Check subscription access
            start = time.monotonic()
            sub_resp = await client.get(
                f"https://management.azure.com/subscriptions/{subscription_id}?api-version=2022-12-01",
                headers=headers,
            )
            latency = int((time.monotonic() - start) * 1000)

            if sub_resp.status_code == 200:
                sub_name = sub_resp.json().get("displayName", subscription_id)
                identity = f"Subscription: {sub_name}"
                permissions.append("Subscription access ✅")
                health_checks.append({
                    "name": "Subscription Access",
                    "status": "healthy",
                    "message": f"Access to '{sub_name}' ({latency}ms)",
                })
            else:
                return None, None, ["Cannot access subscription — check role assignments"], []

            # Check resource group access if provided
            if resource_group_name:
                start = time.monotonic()
                rg_resp = await client.get(
                    f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}?api-version=2023-07-01",
                    headers=headers,
                )
                latency = int((time.monotonic() - start) * 1000)

                if rg_resp.status_code == 200:
                    permissions.append(f"Resource group '{resource_group_name}' ✅")
                    health_checks.append({
                        "name": "Resource Group",
                        "status": "healthy",
                        "message": f"Access to '{resource_group_name}' ({latency}ms)",
                    })
                else:
                    permissions.append(f"Resource group '{resource_group_name}' ❌")
                    health_checks.append({
                        "name": "Resource Group",
                        "status": "degraded",
                        "message": f"Cannot access resource group '{resource_group_name}'",
                    })

        return identity, permissions, errors, health_checks

    except ImportError:
        return None, None, ["httpx not installed — cannot validate Azure credentials"], []
    except Exception as e:
        return None, None, [f"Azure credential validation failed: {str(e)}"], []


async def _validate_gcp(creds: dict) -> tuple[str | None, list[str] | None, list[str], list[dict]]:
    """Validate GCP credentials using service account JSON key."""
    errors = []
    health_checks = []
    project_id = creds.get("project_id")
    service_account_email = creds.get("service_account_email")
    service_account_json = creds.get("key_file")  # JSON upload content

    if not service_account_json:
        # Fallback to legacy field name
        service_account_json = creds.get("service_account_json")

    if not service_account_json:
        return None, None, ["Missing key_file (paste the full JSON key contents)"], []

    try:
        import json
        if isinstance(service_account_json, str):
            try:
                sa_info = json.loads(service_account_json)
            except json.JSONDecodeError:
                return None, None, ["Invalid JSON in key_file"], []
        else:
            sa_info = service_account_json

        sa_project_id = sa_info.get("project_id")
        client_email = sa_info.get("client_email")

        if not sa_project_id or not client_email:
            return None, None, ["JSON key missing project_id or client_email fields"], []

        # Use project_id from field if provided, otherwise from key
        effective_project = project_id or sa_project_id

        # Try to authenticate
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            start = time.monotonic()
            credentials = service_account.Credentials.from_service_account_info(
                sa_info,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            credentials.refresh(Request())
            latency = int((time.monotonic() - start) * 1000)

            identity = f"{client_email} (project: {effective_project})"
            permissions = ["Authentication ✅"]
            health_checks.append({
                "name": "Service Account Auth",
                "status": "healthy",
                "message": f"Authenticated as {client_email} ({latency}ms)",
            })

            # Check Vertex AI access
            import httpx
            async with httpx.AsyncClient() as client:
                start = time.monotonic()
                resp = await client.get(
                    f"https://us-central1-aiplatform.googleapis.com/v1/projects/{effective_project}/locations/us-central1/publishers/google/models",
                    headers={"Authorization": f"Bearer {credentials.token}"},
                )
                latency = int((time.monotonic() - start) * 1000)

                if resp.status_code == 200:
                    permissions.append("Vertex AI access ✅")
                    health_checks.append({
                        "name": "Vertex AI",
                        "status": "healthy",
                        "message": f"Can list models ({latency}ms)",
                    })
                else:
                    permissions.append("Vertex AI access ❌")
                    errors.append("Cannot access Vertex AI — check IAM roles")
                    health_checks.append({
                        "name": "Vertex AI",
                        "status": "error",
                        "message": "Cannot access Vertex AI API",
                    })

            return identity, permissions, errors, health_checks

        except ImportError:
            # Fallback: just validate the JSON structure
            identity = f"{client_email} (project: {effective_project})"
            health_checks.append({
                "name": "JSON Key Validation",
                "status": "healthy",
                "message": "Key structure valid (full validation requires google-auth)",
            })
            return identity, ["JSON key structure valid ✅ (full validation requires google-auth)"], errors, health_checks

    except Exception as e:
        return None, None, [f"GCP credential validation failed: {str(e)}"], []
