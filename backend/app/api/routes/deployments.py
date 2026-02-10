from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.deployment import Deployment
from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.deployment import DeploymentCreate, DeploymentUpdate, DeploymentResponse

router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.get("/", response_model=List[DeploymentResponse])
async def list_deployments(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Deployment).where(Deployment.org_id == user.org_id))
    return result.scalars().all()


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(deployment_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id, Deployment.org_id == user.org_id))
    deployment = result.scalar_one_or_none()
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment


@router.post("/", response_model=DeploymentResponse, status_code=201)
async def create_deployment(data: DeploymentCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    deployment = Deployment(
        org_id=user.org_id,
        model_id=data.model_id,
        provider_id=data.provider_id,
        config=data.config,
        status="pending",
    )
    db.add(deployment)
    await db.flush()
    await db.refresh(deployment)
    return deployment


@router.patch("/{deployment_id}", response_model=DeploymentResponse)
async def update_deployment(deployment_id: UUID, data: DeploymentUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id, Deployment.org_id == user.org_id))
    deployment = result.scalar_one_or_none()
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if data.config is not None:
        deployment.config = data.config
    if data.status is not None:
        deployment.status = data.status
    await db.flush()
    await db.refresh(deployment)
    return deployment


@router.delete("/{deployment_id}", status_code=204)
async def delete_deployment(deployment_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id, Deployment.org_id == user.org_id))
    deployment = result.scalar_one_or_none()
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    await db.delete(deployment)
