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
from app.services.provider_service import (
    get_models_for_provider,
    get_provider_display_name,
    validate_credentials,
    extract_region,
    mock_verify_connection,
    get_aws_provider,
    get_azure_provider,
    get_gcp_provider,
    store_credentials_in_vault,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/providers", tags=["providers"])

DEFAULT_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _to_response(p: CloudProvider, model_count: int = None) -> dict:
    creds = {}
    if p.credentials_encrypted:
        try:
            creds = eval(p.credentials_encrypted) if isinstance(p.credentials_encrypted, str) else {}
        except Exception:
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


@router.get("/", response_model=List[ProviderResponse])
async def list_providers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CloudProvider))
    providers = result.scalars().all()
    responses = []
    for p in providers:
        try:
            models = await get_models_for_provider(p.provider_type, str(p.id))
            responses.append(_to_response(p, len(models)))
        except Exception:
            responses.append(_to_response(p, 0))
    return responses


@router.get("/{provider_id}", response_model=ProviderDetail)
async def get_provider(provider_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id))
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
async def get_provider_summary(provider_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get provider info with masked credentials — safe for display."""
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id))
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
    provider_id: UUID, data: CredentialUpdate, db: AsyncSession = Depends(get_db)
):
    """Update credentials for an existing provider. Validates before saving."""
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Validate credential format
    valid, error = validate_credentials(provider.provider_type, data.credentials)
    if not valid:
        raise HTTPException(status_code=422, detail=error)

    # Validate against real cloud provider
    if provider.provider_type == "aws":
        from app.services.providers.aws_bedrock import AWSBedrockProvider
        prov = AWSBedrockProvider(
            access_key_id=data.credentials["access_key_id"],
            secret_access_key=data.credentials["secret_access_key"],
            region=data.credentials.get("region", "us-east-1"),
        )
        cred_info = await prov.validate_credentials()
        if not cred_info.valid:
            raise HTTPException(status_code=422, detail=f"AWS credential validation failed: {cred_info.message}")
    elif provider.provider_type == "azure":
        from app.services.providers.azure_foundry import AzureFoundryProvider
        prov = AzureFoundryProvider(
            tenant_id=data.credentials["tenant_id"],
            client_id=data.credentials["client_id"],
            client_secret=data.credentials["client_secret"],
            subscription_id=data.credentials["subscription_id"],
            resource_group=data.credentials.get("resource_group", ""),
            endpoint=data.credentials.get("endpoint", ""),
        )
        cred_info = await prov.validate_credentials()
        if not cred_info.valid:
            raise HTTPException(status_code=422, detail=f"Azure credential validation failed: {cred_info.message}")
    elif provider.provider_type == "gcp":
        from app.services.providers.gcp_vertex import GCPVertexProvider
        prov = GCPVertexProvider(
            project_id=data.credentials["project_id"],
            service_account_json=data.credentials["service_account_json"],
            region=data.credentials.get("region", "us-central1"),
        )
        cred_info = await prov.validate_credentials()
        if not cred_info.valid:
            raise HTTPException(status_code=422, detail=f"GCP credential validation failed: {cred_info.message}")

    # Update in Vault
    try:
        await store_credentials_in_vault(str(provider_id), data.credentials)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update credentials in Vault: {e}")

    # Update provider status
    provider.status = "active"
    await db.flush()

    masked_creds = mask_credentials(provider.provider_type, data.credentials)
    models = await get_models_for_provider(provider.provider_type, str(provider.id))
    return ProviderSummary(
        id=provider.id,
        provider_type=provider.provider_type,
        status=provider.status,
        name=get_provider_display_name(provider.provider_type),
        region=extract_region(provider.provider_type, data.credentials),
        model_count=len(models),
        masked_credentials=masked_creds,
        last_validated=provider.created_at,
        created_at=provider.created_at,
    )


@router.post("/connect", response_model=ProviderResponse, status_code=201)
async def connect_provider(data: ProviderConnect, db: AsyncSession = Depends(get_db)):
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
        prov = AzureFoundryProvider(
            tenant_id=data.credentials["tenant_id"],
            client_id=data.credentials["client_id"],
            client_secret=data.credentials["client_secret"],
            subscription_id=data.credentials["subscription_id"],
            resource_group=data.credentials.get("resource_group", ""),
            endpoint=data.credentials.get("endpoint", ""),
        )
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

    # Store credentials in Vault
    try:
        vault_path = await store_credentials_in_vault(str(provider_id), data.credentials)
    except Exception as e:
        logger.warning(f"Vault storage failed, using DB fallback: {e}")
        vault_path = None

    provider = CloudProvider(
        id=provider_id,
        org_id=DEFAULT_ORG_ID,
        provider_type=data.provider_type,
        credentials_encrypted=f"vault:providers/{provider_id}",
        status="active",
    )
    db.add(provider)
    await db.flush()
    await db.refresh(provider)

    models = await get_models_for_provider(provider.provider_type, str(provider.id))
    return _to_response(provider, len(models))


@router.post("/{provider_id}/verify", response_model=VerifyResponse)
async def verify_provider(provider_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id))
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
async def invoke_model(provider_id: UUID, req: InvocationRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id))
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
async def list_provider_models(provider_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id))
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
):
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id))
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
async def delete_provider(provider_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.delete(provider)


@router.post("/", response_model=ProviderResponse, status_code=201)
async def create_provider(data: ProviderCreate, db: AsyncSession = Depends(get_db)):
    provider = CloudProvider(
        org_id=data.org_id,
        provider_type=data.provider_type,
        credentials_encrypted=str(data.credentials) if data.credentials else None,
        status="pending",
    )
    db.add(provider)
    await db.flush()
    await db.refresh(provider)
    return _to_response(provider)


@router.patch("/{provider_id}", response_model=ProviderResponse)
async def update_provider(provider_id: UUID, data: ProviderUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    if data.provider_type is not None:
        provider.provider_type = data.provider_type
    if data.status is not None:
        provider.status = data.status
    if data.credentials is not None:
        provider.credentials_encrypted = str(data.credentials)
    await db.flush()
    await db.refresh(provider)
    return _to_response(provider)
