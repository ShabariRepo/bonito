from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.model import Model
from app.schemas.model import ModelCreate, ModelUpdate, ModelResponse

router = APIRouter(prefix="/models", tags=["models"])


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
