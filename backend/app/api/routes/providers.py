import json
import uuid
import logging
from datetime import date
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.cloud_provider import CloudProvider
from app.schemas.provider import (
    ProviderConnect,
    ProviderCreate,
    ProviderUpdate,
    ProviderResponse,
    ProviderDetail,
    ProviderSummary,
    CredentialUpdate,
    ModelInfo,
    VerifyResponse,
    InvocationRequest,
    InvocationResponse,
    CostDataResponse,
    DailyCostItem,
)
from app.utils.masking import mask_credentials
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.provider_service import (
    get_models_for_provider,
    get_provider_display_name,
    validate_credentials,
    extract_region,
    mock_verify_connection,
    get_aws_provider,
    get_azure_provider,
    get_gcp_provider,
    get_openai_provider,
    get_anthropic_provider,
    get_groq_provider,
    store_credentials_in_vault,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/providers", tags=["providers"])


def _to_response(p: CloudProvider, model_count: int = None) -> dict:
    creds = {}
    if p.credentials_encrypted:
        try:
            creds = json.loads(p.credentials_encrypted) if isinstance(p.credentials_encrypted, str) else {}
        except (json.JSONDecodeError, TypeError):
            pass
    region = extract_region(p.provider_type, creds)
    return {
        "id": p.id,
        "org_id": p.org_id,
        "provider_type": p.provider_type,
        "status": p.status,
        "name": get_provider_display_name(p.provider_type),
        "region": region,
        "model_count": model_count if model_count is not None else 0,
        "created_at": p.created_at,
    }


@router.get("", response_model=List[ProviderResponse])
async def list_providers(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    import asyncio
    result = await db.execute(select(CloudProvider).where(CloudProvider.org_id == user.org_id))
    providers = result.scalars().all()

    async def _count(p):
        try:
            models = await get_models_for_provider(p.provider_type, str(p.id))
            return p, len(models)
        except Exception:
            return p, 0

    pairs = await asyncio.gather(*[_count(p) for p in providers])
    return [_to_response(p, count) for p, count in pairs]


@router.get("/{provider_id}", response_model=ProviderDetail)
async def get_provider(provider_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id, CloudProvider.org_id == user.org_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    models = await get_models_for_provider(provider.provider_type, str(provider.id))
    resp = _to_response(provider, len(models))
    resp["models"] = [m.model_dump() if hasattr(m, 'model_dump') else m for m in models]
    resp["last_verified"] = provider.created_at
    resp["connection_health"] = "healthy" if provider.status == "active" else "degraded"
    return resp


@router.get("/{provider_id}/summary", response_model=ProviderSummary)
async def get_provider_summary(provider_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Get provider info with masked credentials — safe for display."""
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id, CloudProvider.org_id == user.org_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Fetch credentials from Vault and mask them
    masked_creds = {}
    try:
        from app.core.vault import vault_client
        secrets = await vault_client.get_secrets(f"providers/{provider_id}")
        if secrets:
            masked_creds = mask_credentials(provider.provider_type, secrets)
    except Exception as e:
        logger.warning(f"Failed to fetch credentials for masking: {e}")

    models = await get_models_for_provider(provider.provider_type, str(provider.id))
    return ProviderSummary(
        id=provider.id,
        provider_type=provider.provider_type,
        status=provider.status,
        name=get_provider_display_name(provider.provider_type),
        region=extract_region(provider.provider_type, masked_creds),
        model_count=len(models),
        masked_credentials=masked_creds,
        last_validated=provider.created_at,  # TODO: track separately
        created_at=provider.created_at,
    )


@router.put("/{provider_id}/credentials", response_model=ProviderSummary)
async def update_provider_credentials(
    provider_id: UUID, data: CredentialUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """Update credentials for an existing provider. Supports partial updates — 
    empty/missing fields keep their existing values from Vault."""
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id, CloudProvider.org_id == user.org_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Merge with existing credentials — empty fields keep old values
    try:
        from app.core.vault import vault_client
        existing_creds = await vault_client.get_secrets(f"providers/{provider_id}")
    except Exception as e:
        logger.warning(f"Could not fetch existing credentials from Vault: {e}")
        existing_creds = {}
    
    merged = {**existing_creds}
    for key, value in data.credentials.items():
        # Only overwrite if the new value is non-empty and not a masked placeholder
        if value and not (isinstance(value, str) and value.strip() in ("", "••••••••")):
            merged[key] = value
    
    # Validate credential format with merged values
    valid, error = validate_credentials(provider.provider_type, merged)
    if not valid:
        raise HTTPException(status_code=422, detail=error)

    # Validate against real cloud provider using merged credentials
    if provider.provider_type == "aws":
        from app.services.providers.aws_bedrock import AWSBedrockProvider
        prov = AWSBedrockProvider(
            access_key_id=merged["access_key_id"],
            secret_access_key=merged["secret_access_key"],
            region=merged.get("region", "us-east-1"),
        )
        cred_info = await prov.validate_credentials()
        if not cred_info.valid:
            raise HTTPException(status_code=422, detail=f"AWS credential validation failed: {cred_info.message}")
    elif provider.provider_type == "azure":
        from app.services.providers.azure_foundry import AzureFoundryProvider
        azure_mode = merged.get("azure_mode", "openai")  # default to openai for backward compat
        prov = AzureFoundryProvider(
            tenant_id=merged.get("tenant_id", ""),
            client_id=merged.get("client_id", ""),
            client_secret=merged.get("client_secret", ""),
            subscription_id=merged.get("subscription_id", ""),
            resource_group=merged.get("resource_group", ""),
            endpoint=merged.get("endpoint", ""),
            azure_mode=azure_mode,
            api_key=merged.get("api_key", ""),
        )
        cred_info = await prov.validate_credentials()
        if not cred_info.valid:
            raise HTTPException(status_code=422, detail=f"Azure credential validation failed: {cred_info.message}")
    elif provider.provider_type == "gcp":
        from app.services.providers.gcp_vertex import GCPVertexProvider
        prov = GCPVertexProvider(
            project_id=merged["project_id"],
            service_account_json=merged["service_account_json"],
            region=merged.get("region", "us-central1"),
        )
        cred_info = await prov.validate_credentials()
        if not cred_info.valid:
            raise HTTPException(status_code=422, detail=f"GCP credential validation failed: {cred_info.message}")

    # Update in Vault + encrypted DB column using merged credentials
    import os
    from app.core.encryption import encrypt_credentials

    try:
        await store_credentials_in_vault(str(provider_id), merged)
    except Exception as e:
        logger.warning(f"Vault storage failed on update: {e}")

    try:
        secret_key = os.getenv("SECRET_KEY") or os.getenv("ENCRYPTION_KEY")
        if secret_key:
            provider.credentials_encrypted = encrypt_credentials(merged, secret_key)
    except Exception as e:
        logger.warning(f"DB credential encryption failed on update: {e}")

    # Update provider status
    provider.status = "active"
    await db.flush()

    masked_creds = mask_credentials(provider.provider_type, merged)
    models = await get_models_for_provider(provider.provider_type, str(provider.id))
    return ProviderSummary(
        id=provider.id,
        provider_type=provider.provider_type,
        status=provider.status,
        name=get_provider_display_name(provider.provider_type),
        region=extract_region(provider.provider_type, merged),
        model_count=len(models),
        masked_credentials=masked_creds,
        last_validated=provider.created_at,
        created_at=provider.created_at,
    )


@router.post("/connect", response_model=ProviderResponse, status_code=201)
async def connect_provider(data: ProviderConnect, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    # Check provider count limit based on subscription tier
    from app.services.feature_gate import feature_gate
    await feature_gate.require_usage_limit(db, str(user.org_id), "providers")

    # Validate credential format
    valid, error = validate_credentials(data.provider_type, data.credentials)
    if not valid:
        raise HTTPException(status_code=422, detail=error)

    provider_id = uuid.uuid4()

    # Validate credentials against real cloud provider before saving
    if data.provider_type == "aws":
        from app.services.providers.aws_bedrock import AWSBedrockProvider
        prov = AWSBedrockProvider(
            access_key_id=data.credentials["access_key_id"],
            secret_access_key=data.credentials["secret_access_key"],
            region=data.credentials.get("region", "us-east-1"),
        )
        cred_info = await prov.validate_credentials()
        if not cred_info.valid:
            raise HTTPException(status_code=422, detail=f"AWS credential validation failed: {cred_info.message}")
    elif data.provider_type == "azure":
        from app.services.providers.azure_foundry import AzureFoundryProvider
        azure_mode = data.credentials.get("azure_mode", "foundry")  # default to foundry for new setups
        prov = AzureFoundryProvider(
            tenant_id=data.credentials.get("tenant_id", ""),
            client_id=data.credentials.get("client_id", ""),
            client_secret=data.credentials.get("client_secret", ""),
            subscription_id=data.credentials.get("subscription_id", ""),
            resource_group=data.credentials.get("resource_group", ""),
            endpoint=data.credentials.get("endpoint", ""),
            azure_mode=azure_mode,
            api_key=data.credentials.get("api_key", ""),
        )

        # Foundry mode without endpoint = Bonito needs to provision the resource
        if azure_mode == "foundry" and not data.credentials.get("endpoint"):
            # First validate service principal can authenticate
            cred_info = await prov.validate_credentials()
            if not cred_info.valid:
                raise HTTPException(status_code=422, detail=f"Azure credential validation failed: {cred_info.message}")
            # Auto-provision the Foundry resource
            try:
                org_prefix = str(user.org_id)[:8]
                provisioned = await prov.provision_foundry_resource(
                    resource_name=f"bonito-ai-{org_prefix}",
                    location="eastus",
                )
                # Merge provisioned values back into credentials
                data.credentials["endpoint"] = provisioned["endpoint"]
                data.credentials["api_key"] = provisioned["api_key"]
                data.credentials["resource_group"] = provisioned["resource_group"]
                data.credentials["azure_mode"] = "foundry"
                logger.info(f"Auto-provisioned Azure AI Foundry: {provisioned['endpoint']}")
            except RuntimeError as e:
                raise HTTPException(
                    status_code=422,
                    detail=f"Azure AI resource provisioning failed: {str(e)}. "
                    f"Ensure the service principal has 'Cognitive Services Contributor' role.",
                )
        else:
            cred_info = await prov.validate_credentials()
            if not cred_info.valid:
                raise HTTPException(status_code=422, detail=f"Azure credential validation failed: {cred_info.message}")
    elif data.provider_type == "gcp":
        from app.services.providers.gcp_vertex import GCPVertexProvider
        prov = GCPVertexProvider(
            project_id=data.credentials["project_id"],
            service_account_json=data.credentials["service_account_json"],
            region=data.credentials.get("region", "us-central1"),
        )
        cred_info = await prov.validate_credentials()
        if not cred_info.valid:
            raise HTTPException(status_code=422, detail=f"GCP credential validation failed: {cred_info.message}")
    elif data.provider_type == "openai":
        from app.services.providers.openai_direct import OpenAIDirectProvider
        prov = OpenAIDirectProvider(
            api_key=data.credentials["api_key"],
            organization_id=data.credentials.get("organization_id"),
        )
        cred_info = await prov.validate_credentials()
        if not cred_info.valid:
            raise HTTPException(status_code=422, detail=f"OpenAI credential validation failed: {cred_info.message}")
    elif data.provider_type == "anthropic":
        from app.services.providers.anthropic_direct import AnthropicDirectProvider
        prov = AnthropicDirectProvider(
            api_key=data.credentials["api_key"],
        )
        cred_info = await prov.validate_credentials()
        if not cred_info.valid:
            raise HTTPException(status_code=422, detail=f"Anthropic credential validation failed: {cred_info.message}")
    elif data.provider_type == "groq":
        from app.services.providers.groq_provider import GroqProvider
        prov = GroqProvider(
            api_key=data.credentials["api_key"],
        )
        cred_info = await prov.validate_credentials()
        if not cred_info.valid:
            raise HTTPException(status_code=422, detail=f"Groq credential validation failed: {cred_info.message}")

    # Store credentials in Vault + encrypted DB column
    import os
    from app.core.encryption import encrypt_credentials

    encrypted_creds = f"vault:providers/{provider_id}"  # fallback reference
    try:
        secret_key = os.getenv("SECRET_KEY") or os.getenv("ENCRYPTION_KEY")
        if secret_key:
            encrypted_creds = encrypt_credentials(data.credentials, secret_key)
    except Exception as e:
        logger.warning(f"Credential encryption failed: {e}")

    try:
        await store_credentials_in_vault(str(provider_id), data.credentials)
    except Exception as e:
        logger.warning(f"Vault storage failed (DB fallback will be used): {e}")

    provider = CloudProvider(
        id=provider_id,
        org_id=user.org_id,
        provider_type=data.provider_type,
        credentials_encrypted=encrypted_creds,
        status="active",
    )
    db.add(provider)
    await db.flush()
    await db.refresh(provider)

    # Sync discovered models into DB
    from app.api.routes.models import sync_provider_models
    sync_result = await sync_provider_models(provider, db)
    model_count = sync_result["count"] if isinstance(sync_result, dict) else sync_result
    logger.info(f"Synced {model_count} models for {data.provider_type} provider {provider_id}")

    return _to_response(provider, model_count)


@router.post("/{provider_id}/verify", response_model=VerifyResponse)
async def verify_provider(provider_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id, CloudProvider.org_id == user.org_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Get the real provider instance
    try:
        if provider.provider_type == "aws":
            cloud_prov = await get_aws_provider(str(provider_id))
        elif provider.provider_type == "azure":
            cloud_prov = await get_azure_provider(str(provider_id))
        elif provider.provider_type == "gcp":
            cloud_prov = await get_gcp_provider(str(provider_id))
        elif provider.provider_type == "openai":
            cloud_prov = await get_openai_provider(str(provider_id))
        elif provider.provider_type == "anthropic":
            cloud_prov = await get_anthropic_provider(str(provider_id))
        elif provider.provider_type == "groq":
            cloud_prov = await get_groq_provider(str(provider_id))
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider type: {provider.provider_type}")

        health = await cloud_prov.health_check()
        if health.healthy:
            provider.status = "active"
            await db.flush()
            models = await cloud_prov.list_models()
            return VerifyResponse(
                success=True,
                message=f"Connected! Found {len(models)} models",
                latency_ms=health.latency_ms,
                account_id=health.account_id,
                model_count=len(models),
                region=getattr(cloud_prov, '_region', ''),
            )
        else:
            provider.status = "error"
            await db.flush()
            return VerifyResponse(success=False, message=health.message, latency_ms=health.latency_ms)
    except HTTPException:
        raise
    except Exception as e:
        provider.status = "error"
        await db.flush()
        return VerifyResponse(success=False, message=str(e))


@router.post("/{provider_id}/invoke", response_model=InvocationResponse)
async def invoke_model(provider_id: UUID, req: InvocationRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id, CloudProvider.org_id == user.org_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    try:
        if provider.provider_type == "aws":
            cloud_prov = await get_aws_provider(str(provider_id))
        elif provider.provider_type == "azure":
            cloud_prov = await get_azure_provider(str(provider_id))
        elif provider.provider_type == "gcp":
            cloud_prov = await get_gcp_provider(str(provider_id))
        elif provider.provider_type == "openai":
            cloud_prov = await get_openai_provider(str(provider_id))
        elif provider.provider_type == "anthropic":
            cloud_prov = await get_anthropic_provider(str(provider_id))
        elif provider.provider_type == "groq":
            cloud_prov = await get_groq_provider(str(provider_id))
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider.provider_type}")

        inv_result = await cloud_prov.invoke_model(
            model_id=req.model_id,
            prompt=req.prompt,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
        )
        return InvocationResponse(
            response_text=inv_result.response_text,
            input_tokens=inv_result.input_tokens,
            output_tokens=inv_result.output_tokens,
            latency_ms=inv_result.latency_ms,
            estimated_cost=inv_result.estimated_cost,
            model_id=inv_result.model_id,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Invocation error: {e}")
        raise HTTPException(status_code=500, detail="Model invocation failed")


@router.get("/{provider_id}/models", response_model=List[ModelInfo])
async def list_provider_models(provider_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id, CloudProvider.org_id == user.org_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return await get_models_for_provider(provider.provider_type, str(provider.id))


@router.get("/{provider_id}/costs", response_model=CostDataResponse)
async def get_provider_costs(
    provider_id: UUID,
    start_date: str = None,
    end_date: str = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id, CloudProvider.org_id == user.org_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    from datetime import timedelta, datetime as dt
    end = date.fromisoformat(end_date) if end_date else date.today()
    start = date.fromisoformat(start_date) if start_date else end - timedelta(days=30)

    try:
        if provider.provider_type == "aws":
            cloud_prov = await get_aws_provider(str(provider_id))
        elif provider.provider_type == "azure":
            cloud_prov = await get_azure_provider(str(provider_id))
        elif provider.provider_type == "gcp":
            cloud_prov = await get_gcp_provider(str(provider_id))
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider.provider_type}")

        cost_data = await cloud_prov.get_costs(start, end)
        return CostDataResponse(
            total=cost_data.total,
            currency=cost_data.currency,
            start_date=cost_data.start_date,
            end_date=cost_data.end_date,
            daily_costs=[
                DailyCostItem(
                    date=dc.date,
                    amount=dc.amount,
                    currency=dc.currency,
                    service=dc.service,
                    usage_type=dc.usage_type,
                )
                for dc in cost_data.daily_costs
            ],
        )
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/{provider_id}", status_code=204)
async def delete_provider(provider_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id, CloudProvider.org_id == user.org_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.delete(provider)


@router.post("/{provider_id}/provision-azure", response_model=VerifyResponse)
async def provision_azure_resource(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Provision an Azure AI Foundry resource using stored service principal credentials.

    Bonito creates the AIServices resource, retrieves API keys, and updates
    the stored credentials — the customer never touches Azure Portal.
    """
    result = await db.execute(
        select(CloudProvider).where(
            CloudProvider.id == provider_id,
            CloudProvider.org_id == user.org_id,
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    if provider.provider_type != "azure":
        raise HTTPException(status_code=400, detail="Provisioning is only for Azure providers")

    try:
        cloud_prov = await get_azure_provider(str(provider_id))

        # Provision the Foundry resource
        org_name = str(user.org_id)[:8]  # short org prefix for naming
        provisioned = await cloud_prov.provision_foundry_resource(
            resource_name=f"bonito-ai-{org_name}",
            location="eastus",
        )

        # Update stored credentials with the provisioned endpoint + API key
        from app.core.vault import vault_client as vc
        existing_creds = {}
        try:
            existing_creds = await vc.get_secrets(f"providers/{provider_id}") or {}
        except Exception:
            pass

        updated_creds = {
            **existing_creds,
            "endpoint": provisioned["endpoint"],
            "api_key": provisioned["api_key"],
            "resource_group": provisioned["resource_group"],
            "azure_mode": "foundry",
        }
        await store_credentials_in_vault(str(provider_id), updated_creds)

        # Update encrypted DB column too
        import os
        from app.core.encryption import encrypt_credentials
        secret_key = os.getenv("SECRET_KEY") or os.getenv("ENCRYPTION_KEY")
        if secret_key:
            provider.credentials_encrypted = encrypt_credentials(updated_creds, secret_key)

        provider.status = "active"
        await db.flush()

        # Sync models
        from app.api.routes.models import sync_provider_models
        sync_result = await sync_provider_models(provider, db)
        model_count = sync_result["count"] if isinstance(sync_result, dict) else sync_result

        return VerifyResponse(
            success=True,
            message=f"Azure AI Foundry provisioned! Endpoint: {provisioned['endpoint']}. Found {model_count} models.",
            latency_ms=0,
            account_id=provisioned["resource_name"],
            model_count=model_count,
            region=provisioned.get("location", "eastus"),
        )

    except RuntimeError as e:
        return VerifyResponse(success=False, message=str(e))
    except Exception as e:
        logger.error(f"Azure provisioning error: {e}")
        return VerifyResponse(success=False, message=f"Provisioning failed: {str(e)}")


@router.post("", response_model=ProviderResponse, status_code=201)
async def create_provider(data: ProviderCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    provider = CloudProvider(
        org_id=data.org_id,
        provider_type=data.provider_type,
        credentials_encrypted=json.dumps(dict(data.credentials)) if data.credentials else None,
        status="pending",
    )
    db.add(provider)
    await db.flush()
    await db.refresh(provider)
    return _to_response(provider)


@router.patch("/{provider_id}", response_model=ProviderResponse)
async def update_provider(provider_id: UUID, data: ProviderUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id, CloudProvider.org_id == user.org_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    if data.provider_type is not None:
        provider.provider_type = data.provider_type
    if data.status is not None:
        provider.status = data.status
    if data.credentials is not None:
        provider.credentials_encrypted = json.dumps(dict(data.credentials))
    await db.flush()
    await db.refresh(provider)
    return _to_response(provider)
