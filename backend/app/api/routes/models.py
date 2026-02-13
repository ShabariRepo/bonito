import logging
import time
import asyncio
from uuid import UUID
from typing import List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.model import Model
from app.models.cloud_provider import CloudProvider
from app.models.gateway import GatewayRequest
from app.schemas.model import (
    ModelCreate, ModelUpdate, ModelResponse, ModelDetailsResponse,
    PlaygroundRequest, PlaygroundResponse, CompareRequest, CompareResponse,
    CompareResult, UsageStats, ProviderInfo, PlaygroundUsage
)
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.provider_service import get_models_for_provider
from app.services.gateway import get_router, chat_completion
from app.models.policy import Policy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["models"])


async def sync_provider_models(provider: CloudProvider, db: AsyncSession) -> int:
    """Fetch models from cloud API and upsert into DB. Returns count synced."""
    try:
        cloud_models = await get_models_for_provider(provider.provider_type, str(provider.id))
    except Exception as e:
        logger.error(f"Failed to fetch models for {provider.provider_type}: {e}")
        return 0

    if not cloud_models:
        return 0

    # Delete existing models for this provider, then re-insert
    await db.execute(delete(Model).where(Model.provider_id == provider.id))

    count = 0
    for m in cloud_models:
        model_id = getattr(m, "provider_model_id", None) or getattr(m, "model_id", None) or getattr(m, "id", str(count))
        display_name = getattr(m, "name", None) or getattr(m, "model_name", None) or model_id
        capabilities_raw = getattr(m, "capabilities", [])
        capabilities = capabilities_raw if isinstance(capabilities_raw, dict) else {"types": capabilities_raw}
        pricing = {}
        for field in ("input_price_per_1k", "output_price_per_1k", "pricing_tier", "context_window"):
            val = getattr(m, field, None)
            if val is not None:
                pricing[field] = val
        status = getattr(m, "status", "available")
        pricing["status"] = status

        db_model = Model(
            provider_id=provider.id,
            model_id=str(model_id),
            display_name=str(display_name),
            capabilities=capabilities,
            pricing_info=pricing,
        )
        db.add(db_model)
        count += 1

    await db.flush()
    return count


@router.post("/sync")
async def sync_all_models(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Sync models from all connected providers into the DB."""
    result = await db.execute(select(CloudProvider).where(CloudProvider.status == "active", CloudProvider.org_id == user.org_id))
    providers = result.scalars().all()
    total = 0
    details = {}
    for p in providers:
        count = await sync_provider_models(p, db)
        total += count
        details[p.provider_type] = count
    return {"synced": total, "details": details}


@router.post("/sync/{provider_id}")
async def sync_provider(provider_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Sync models for a specific provider."""
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id, CloudProvider.org_id == user.org_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(404, "Provider not found")
    count = await sync_provider_models(provider, db)
    return {"synced": count, "provider": provider.provider_type}


@router.get("/", response_model=List[ModelResponse])
async def list_models(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Model, CloudProvider.provider_type).join(CloudProvider, Model.provider_id == CloudProvider.id).where(CloudProvider.org_id == user.org_id)
    )
    models = []
    for model, provider_type in result.all():
        model.provider_type = provider_type
        models.append(model)
    return models


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(model_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Model).join(CloudProvider, Model.provider_id == CloudProvider.id).where(Model.id == model_id, CloudProvider.org_id == user.org_id)
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.post("/", response_model=ModelResponse, status_code=201)
async def create_model(data: ModelCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    model = Model(
        provider_id=data.provider_id,
        model_id=data.model_id,
        display_name=data.display_name,
        capabilities=data.capabilities,
        pricing_info=data.pricing_info,
    )
    db.add(model)
    await db.flush()
    await db.refresh(model)
    return model


@router.patch("/{model_id}", response_model=ModelResponse)
async def update_model(model_id: UUID, data: ModelUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Model).join(CloudProvider, Model.provider_id == CloudProvider.id).where(Model.id == model_id, CloudProvider.org_id == user.org_id)
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    if data.display_name is not None:
        model.display_name = data.display_name
    if data.capabilities is not None:
        model.capabilities = data.capabilities
    if data.pricing_info is not None:
        model.pricing_info = data.pricing_info
    await db.flush()
    await db.refresh(model)
    return model


@router.delete("/{model_id}", status_code=204)
async def delete_model(model_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Model).join(CloudProvider, Model.provider_id == CloudProvider.id).where(Model.id == model_id, CloudProvider.org_id == user.org_id)
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    await db.delete(model)


@router.get("/{model_id}/details", response_model=ModelDetailsResponse)
async def get_model_details(model_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Get enriched model details including usage stats and provider info."""
    # Get model with provider info
    result = await db.execute(
        select(Model, CloudProvider)
        .join(CloudProvider, Model.provider_id == CloudProvider.id)
        .where(Model.id == model_id, CloudProvider.org_id == user.org_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Model not found")
    
    model, provider = row

    # Get usage stats for this specific model
    usage_result = await db.execute(
        select(
            func.count(GatewayRequest.id).label("total_requests"),
            func.coalesce(func.sum(GatewayRequest.input_tokens + GatewayRequest.output_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(GatewayRequest.cost), 0).label("total_cost")
        ).where(
            and_(
                GatewayRequest.org_id == user.org_id,
                GatewayRequest.model_requested == model.model_id,
                GatewayRequest.status == "success"
            )
        )
    )
    usage_row = usage_result.first()

    # Get daily usage for the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_usage_result = await db.execute(
        select(
            func.date(GatewayRequest.created_at).label("date"),
            func.count(GatewayRequest.id).label("requests"),
            func.coalesce(func.sum(GatewayRequest.cost), 0).label("cost")
        ).where(
            and_(
                GatewayRequest.org_id == user.org_id,
                GatewayRequest.model_requested == model.model_id,
                GatewayRequest.status == "success",
                GatewayRequest.created_at >= thirty_days_ago
            )
        ).group_by(func.date(GatewayRequest.created_at)).order_by("date")
    )
    
    requests_by_day = [
        {"date": str(row[0]), "requests": row[1], "cost": float(row[2])}
        for row in daily_usage_result.all()
    ]

    usage_stats = UsageStats(
        total_requests=usage_row[0] or 0,
        total_tokens=int(usage_row[1] or 0),
        total_cost=float(usage_row[2] or 0),
        requests_by_day=requests_by_day
    )

    provider_info = ProviderInfo(
        id=provider.id,
        provider_type=provider.provider_type,
        status=provider.status,
        region=None  # Could be extracted from provider credentials if needed
    )

    # Extract pricing and context window from pricing_info
    pricing_info = model.pricing_info or {}
    context_window = pricing_info.get("context_window")
    input_price = pricing_info.get("input_price_per_1k")
    output_price = pricing_info.get("output_price_per_1k")

    return ModelDetailsResponse(
        id=model.id,
        provider_id=model.provider_id,
        model_id=model.model_id,
        display_name=model.display_name,
        provider_type=provider.provider_type,
        capabilities=model.capabilities,
        pricing_info=model.pricing_info,
        created_at=model.created_at,
        provider_info=provider_info,
        usage_stats=usage_stats,
        context_window=context_window,
        input_price_per_1k=input_price,
        output_price_per_1k=output_price
    )


async def _check_governance_policies(db: AsyncSession, org_id: UUID, tokens: int) -> None:
    """Check if the request violates any governance policies."""
    # Check token limits from policies
    result = await db.execute(
        select(Policy).where(
            and_(
                Policy.org_id == org_id,
                Policy.type == "token_limits",
                Policy.enabled.is_(True)
            )
        )
    )
    policy = result.scalar_one_or_none()
    if policy and policy.rules_json:
        max_tokens = policy.rules_json.get("max_tokens_per_request")
        if max_tokens and tokens > max_tokens:
            raise HTTPException(
                status_code=403,
                detail=f"Request exceeds token limit of {max_tokens} tokens"
            )


@router.post("/{model_id}/playground", response_model=PlaygroundResponse)
async def playground_execute(
    model_id: UUID,
    request_data: PlaygroundRequest,
    stream: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Execute a playground request against the specified model."""
    # Get the model and verify it belongs to the user's org
    result = await db.execute(
        select(Model, CloudProvider)
        .join(CloudProvider, Model.provider_id == CloudProvider.id)
        .where(Model.id == model_id, CloudProvider.org_id == user.org_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Model not found")
    
    model, provider = row
    
    # Check governance policies
    max_tokens = request_data.max_tokens or 1000
    await _check_governance_policies(db, user.org_id, max_tokens)
    
    # Prepare the request for the gateway
    gateway_request = {
        "model": model.model_id,
        "messages": [{"role": msg.role, "content": msg.content} for msg in request_data.messages],
        "temperature": request_data.temperature,
        "max_tokens": request_data.max_tokens,
        "stream": stream
    }
    
    # Route directly through provider using litellm (supports any model in catalog)
    start_time = time.time()
    try:
        import litellm
        from app.services.provider_service import _get_provider_secrets
        from app.models.gateway import GatewayRequest as LogEntry
        
        secrets = await _get_provider_secrets(str(provider.id))
        
        # Build litellm model string + auth params based on provider type
        litellm_params: dict = {}
        if provider.provider_type == "aws":
            gateway_request["model"] = f"bedrock/{model.model_id}"
            litellm_params["aws_access_key_id"] = secrets.get("access_key_id", "")
            litellm_params["aws_secret_access_key"] = secrets.get("secret_access_key", "")
            litellm_params["aws_region_name"] = secrets.get("region", "us-east-1")
        elif provider.provider_type == "azure":
            gateway_request["model"] = f"azure/{model.model_id}"
            litellm_params["api_base"] = secrets.get("endpoint", "")
            litellm_params["api_key"] = secrets.get("api_key") or secrets.get("client_secret", "")
            litellm_params["api_version"] = "2024-02-01"
        elif provider.provider_type == "gcp":
            gateway_request["model"] = f"vertex_ai/{model.model_id}"
            litellm_params["vertex_project"] = secrets.get("project_id", "")
            litellm_params["vertex_location"] = secrets.get("region", "us-central1")
            sa_json = secrets.get("service_account_json")
            if sa_json:
                import json as _json
                litellm_params["vertex_credentials"] = _json.dumps(sa_json) if isinstance(sa_json, dict) else sa_json
        elif provider.provider_type == "openai":
            gateway_request["model"] = f"openai/{model.model_id}"
            litellm_params["api_key"] = secrets.get("api_key", "")
        elif provider.provider_type == "anthropic":
            gateway_request["model"] = f"anthropic/{model.model_id}"
            litellm_params["api_key"] = secrets.get("api_key", "")
        
        response = await litellm.acompletion(**gateway_request, **litellm_params)
        
        # Create log entry
        log_entry = LogEntry(
            org_id=user.org_id,
            user_id=user.id,
            model_requested=model.model_id,
            model_used=getattr(response, "model", model.model_id),
            provider=provider.provider_type,
            input_tokens=getattr(response.usage, "prompt_tokens", 0) if hasattr(response, 'usage') else 0,
            output_tokens=getattr(response.usage, "completion_tokens", 0) if hasattr(response, 'usage') else 0,
            cost=0.0,  # Will be calculated below
            latency_ms=int((time.time() - start_time) * 1000),
            status="success"
        )
        db.add(log_entry)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Extract response content
        if stream:
            # For streaming, we'd return the response directly
            # For now, treat as non-streaming for simplicity
            pass
            
        content = ""
        if hasattr(response, 'choices') and len(response.choices) > 0:
            if hasattr(response.choices[0], 'message'):
                content = response.choices[0].message.content or ""
        elif isinstance(response, dict) and response.get("choices"):
            content = response["choices"][0].get("message", {}).get("content", "")
        
        if hasattr(response, 'usage'):
            usage = response.usage
            prompt_tokens = getattr(usage, 'prompt_tokens', 0)
            completion_tokens = getattr(usage, 'completion_tokens', 0)
        elif isinstance(response, dict) and response.get("usage"):
            usage = response["usage"]
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
        else:
            prompt_tokens = 0
            completion_tokens = 0
        
        total_tokens = prompt_tokens + completion_tokens
        
        # Calculate cost (basic estimation if not provided)
        cost = 0.0
        if hasattr(response, 'cost'):
            cost = response.cost
        elif model.pricing_info:
            input_price = model.pricing_info.get("input_price_per_1k", 0)
            output_price = model.pricing_info.get("output_price_per_1k", 0)
            cost = (prompt_tokens / 1000 * input_price) + (completion_tokens / 1000 * output_price)
        
        playground_usage = PlaygroundUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens
        )
        
        return PlaygroundResponse(
            response=content,
            usage=playground_usage,
            cost=cost,
            latency_ms=latency_ms,
            provider=provider.provider_type
        )
        
    except Exception as e:
        logger.error(f"Playground execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Model execution failed: {str(e)}")


@router.post("/compare", response_model=CompareResponse)
async def compare_models(
    request_data: CompareRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Compare multiple models with the same prompt."""
    if len(request_data.model_ids) > 4:
        raise HTTPException(status_code=400, detail="Maximum 4 models can be compared at once")
    
    if len(request_data.model_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 models must be selected for comparison")
    
    # Get all models and verify they belong to the user's org
    result = await db.execute(
        select(Model, CloudProvider)
        .join(CloudProvider, Model.provider_id == CloudProvider.id)
        .where(
            and_(
                Model.id.in_(request_data.model_ids),
                CloudProvider.org_id == user.org_id
            )
        )
    )
    rows = result.all()
    
    if len(rows) != len(request_data.model_ids):
        raise HTTPException(status_code=404, detail="One or more models not found")
    
    # Check governance policies for each model
    max_tokens = request_data.max_tokens or 1000
    await _check_governance_policies(db, user.org_id, max_tokens)
    
    # Execute requests concurrently
    async def execute_single_model(model_row):
        model, provider = model_row
        try:
            gateway_request = {
                "model": model.model_id,
                "messages": [{"role": msg.role, "content": msg.content} for msg in request_data.messages],
                "temperature": request_data.temperature,
                "max_tokens": request_data.max_tokens
            }
            
            start_time = time.time()
            
            # Use router directly instead of chat_completion
            router = await get_router(db, user.org_id)
            response = await router.acompletion(**gateway_request)
            
            # Create log entry
            from app.models.gateway import GatewayRequest as LogEntry
            log_entry = LogEntry(
                org_id=user.org_id,
                user_id=user.id,
                model_requested=model.model_id,
                model_used=getattr(response, "model", model.model_id),
                provider=provider.provider_type,
                input_tokens=getattr(response.usage, "prompt_tokens", 0) if hasattr(response, 'usage') else 0,
                output_tokens=getattr(response.usage, "completion_tokens", 0) if hasattr(response, 'usage') else 0,
                cost=0.0,  # Will be calculated below
                latency_ms=int((time.time() - start_time) * 1000),
                status="success"
            )
            db.add(log_entry)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            content = ""
            if hasattr(response, 'choices') and len(response.choices) > 0:
                if hasattr(response.choices[0], 'message'):
                    content = response.choices[0].message.content or ""
            elif isinstance(response, dict) and response.get("choices"):
                content = response["choices"][0].get("message", {}).get("content", "")
            
            if hasattr(response, 'usage'):
                usage = response.usage
                prompt_tokens = getattr(usage, 'prompt_tokens', 0)
                completion_tokens = getattr(usage, 'completion_tokens', 0)
            elif isinstance(response, dict) and response.get("usage"):
                usage = response["usage"]
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
            else:
                prompt_tokens = 0
                completion_tokens = 0
            
            total_tokens = prompt_tokens + completion_tokens
            
            # Calculate cost
            cost = 0.0
            if hasattr(response, 'cost'):
                cost = response.cost
            elif model.pricing_info:
                input_price = model.pricing_info.get("input_price_per_1k", 0)
                output_price = model.pricing_info.get("output_price_per_1k", 0)
                cost = (prompt_tokens / 1000 * input_price) + (completion_tokens / 1000 * output_price)
            
            playground_usage = PlaygroundUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens
            )
            
            return CompareResult(
                model_id=model.id,
                display_name=model.display_name,
                response=content,
                usage=playground_usage,
                cost=cost,
                latency_ms=latency_ms,
                provider=provider.provider_type
            )
            
        except Exception as e:
            logger.error(f"Model {model.display_name} execution failed: {e}")
            return CompareResult(
                model_id=model.id,
                display_name=model.display_name,
                response="",
                usage=PlaygroundUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                cost=0.0,
                latency_ms=0,
                provider=provider.provider_type,
                error=str(e)
            )
    
    # Execute all models concurrently
    results = await asyncio.gather(*[execute_single_model(row) for row in rows])
    
    return CompareResponse(results=results)
