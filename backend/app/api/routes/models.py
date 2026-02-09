import logging
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.model import Model
from app.models.cloud_provider import CloudProvider
from app.schemas.model import ModelCreate, ModelUpdate, ModelResponse
from app.services.provider_service import get_models_for_provider

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
async def sync_all_models(db: AsyncSession = Depends(get_db)):
    """Sync models from all connected providers into the DB."""
    result = await db.execute(select(CloudProvider).where(CloudProvider.status == "active"))
    providers = result.scalars().all()
    total = 0
    details = {}
    for p in providers:
        count = await sync_provider_models(p, db)
        total += count
        details[p.provider_type] = count
    return {"synced": total, "details": details}


@router.post("/sync/{provider_id}")
async def sync_provider(provider_id: UUID, db: AsyncSession = Depends(get_db)):
    """Sync models for a specific provider."""
    result = await db.execute(select(CloudProvider).where(CloudProvider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(404, "Provider not found")
    count = await sync_provider_models(provider, db)
    return {"synced": count, "provider": provider.provider_type}


@router.get("/", response_model=List[ModelResponse])
async def list_models(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Model))
    return result.scalars().all()


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(model_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Model).where(Model.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.post("/", response_model=ModelResponse, status_code=201)
async def create_model(data: ModelCreate, db: AsyncSession = Depends(get_db)):
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
async def update_model(model_id: UUID, data: ModelUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Model).where(Model.id == model_id))
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
async def delete_model(model_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Model).where(Model.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    await db.delete(model)
