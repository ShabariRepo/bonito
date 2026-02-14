"""
Deployment API — Provision and manage model deployments on customer clouds.

Endpoints:
- GET    /deployments/         — list deployments for org
- POST   /deployments/         — create a new deployment (provisions on cloud)
- GET    /deployments/{id}     — get deployment details
- POST   /deployments/{id}/status  — refresh status from cloud provider
- PATCH  /deployments/{id}     — scale/update deployment
- DELETE /deployments/{id}     — delete deployment + cloud resource
- POST   /deployments/estimate — cost estimation before deploying
"""

import logging
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import get_db
from app.models.deployment import Deployment
from app.models.model import Model
from app.models.cloud_provider import CloudProvider
from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.deployment import DeploymentCreate, DeploymentUpdate, DeploymentResponse
from app.services.deployment_service import (
    estimate_cost,
    deploy_aws,
    deploy_azure,
    deploy_gcp,
    get_aws_deployment_status,
    get_azure_deployment_status,
    scale_aws_deployment,
    delete_aws_deployment,
    delete_azure_deployment,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/deployments", tags=["deployments"])


async def _get_provider_secrets(provider_id: str) -> dict:
    """Get credentials from Vault for a provider."""
    from app.core.vault import vault_client
    try:
        return await vault_client.get_secrets(f"providers/{provider_id}")
    except Exception:
        return {}


@router.get("/", response_model=List[DeploymentResponse])
async def list_deployments(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    result = await db.execute(
        select(Deployment).where(Deployment.org_id == user.org_id).order_by(Deployment.created_at.desc())
    )
    return result.scalars().all()


from pydantic import BaseModel as PydanticBase

class EstimateRequest(PydanticBase):
    model_id: UUID
    config: dict = {}

@router.post("/estimate")
async def estimate_deployment_cost(
    body: EstimateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get cost estimate for a deployment before creating it."""
    result = await db.execute(
        select(Model, CloudProvider)
        .join(CloudProvider, Model.provider_id == CloudProvider.id)
        .where(Model.id == body.model_id, CloudProvider.org_id == user.org_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Model not found")
    
    model, provider = row
    est = estimate_cost(provider.provider_type, model.model_id, body.config)
    
    return {
        "model_id": str(body.model_id),
        "model_name": model.display_name,
        "provider": provider.provider_type,
        "hourly": est.hourly,
        "daily": est.daily,
        "monthly": est.monthly,
        "unit": est.unit,
        "notes": est.notes,
    }


@router.post("/", response_model=DeploymentResponse, status_code=201)
async def create_deployment(
    data: DeploymentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new deployment — provisions resources on the customer's cloud."""
    # Get model and provider
    result = await db.execute(
        select(Model, CloudProvider)
        .join(CloudProvider, Model.provider_id == CloudProvider.id)
        .where(Model.id == data.model_id, CloudProvider.org_id == user.org_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Model not found")
    
    model, provider = row
    secrets = await _get_provider_secrets(str(provider.id))
    
    config = data.config or {}
    config["name"] = config.get("name", f"bonito-{model.model_id.split('.')[-1][:20].replace('/', '-')}")
    
    # Provision on cloud
    if provider.provider_type == "aws":
        deploy_result = await deploy_aws(
            model_id=model.model_id,
            config=config,
            access_key_id=secrets.get("access_key_id", ""),
            secret_access_key=secrets.get("secret_access_key", ""),
            region=secrets.get("region", "us-east-1"),
        )
    elif provider.provider_type == "azure":
        deploy_result = await deploy_azure(
            model_id=model.model_id,
            config=config,
            tenant_id=secrets.get("tenant_id", ""),
            client_id=secrets.get("client_id", ""),
            client_secret=secrets.get("client_secret", ""),
            endpoint=secrets.get("endpoint", ""),
        )
    elif provider.provider_type == "gcp":
        deploy_result = await deploy_gcp(
            model_id=model.model_id,
            config=config,
            project_id=secrets.get("project_id", ""),
            service_account_json=secrets.get("service_account_json", "{}"),
            region=secrets.get("region", "us-central1"),
        )
    else:
        raise HTTPException(400, f"Deployment not supported for provider: {provider.provider_type}")
    
    if not deploy_result.success:
        raise HTTPException(422, deploy_result.message)
    
    # Compute cost estimate
    est = estimate_cost(provider.provider_type, model.model_id, config)
    
    # Store deployment in DB
    deployment = Deployment(
        org_id=user.org_id,
        model_id=model.id,
        provider_id=provider.id,
        config={
            **config,
            "cloud_resource_id": deploy_result.cloud_resource_id,
            "endpoint_url": deploy_result.endpoint_url,
            "provider_type": provider.provider_type,
            "model_display_name": model.display_name,
            "cloud_model_id": model.model_id,
            "config_applied": deploy_result.config_applied,
            "cost_estimate": {
                "hourly": est.hourly,
                "daily": est.daily,
                "monthly": est.monthly,
                "unit": est.unit,
                "notes": est.notes,
            },
            "deploy_message": deploy_result.message,
        },
        status=deploy_result.status,
    )
    db.add(deployment)
    await db.flush()
    await db.refresh(deployment)
    return deployment


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Deployment).where(Deployment.id == deployment_id, Deployment.org_id == user.org_id)
    )
    deployment = result.scalar_one_or_none()
    if not deployment:
        raise HTTPException(404, "Deployment not found")
    return deployment


@router.post("/{deployment_id}/status")
async def refresh_deployment_status(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Refresh deployment status from cloud provider."""
    result = await db.execute(
        select(Deployment, CloudProvider)
        .join(CloudProvider, Deployment.provider_id == CloudProvider.id)
        .where(Deployment.id == deployment_id, Deployment.org_id == user.org_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Deployment not found")
    
    deployment, provider = row
    secrets = await _get_provider_secrets(str(provider.id))
    config = deployment.config or {}
    cloud_resource_id = config.get("cloud_resource_id", "")
    
    cloud_status = {}
    if provider.provider_type == "aws" and cloud_resource_id:
        cloud_status = await get_aws_deployment_status(
            cloud_resource_id=cloud_resource_id,
            access_key_id=secrets.get("access_key_id", ""),
            secret_access_key=secrets.get("secret_access_key", ""),
            region=secrets.get("region", "us-east-1"),
        )
        # Map AWS status to our status
        aws_status = cloud_status.get("status", "").lower()
        if aws_status == "inservice":
            deployment.status = "active"
        elif aws_status in ("creating", "updating"):
            deployment.status = "deploying"
        elif aws_status == "failed":
            deployment.status = "error"
        
    elif provider.provider_type == "azure":
        deployment_name = cloud_resource_id or config.get("name", "")
        if deployment_name:
            cloud_status = await get_azure_deployment_status(
                deployment_name=deployment_name,
                tenant_id=secrets.get("tenant_id", ""),
                client_id=secrets.get("client_id", ""),
                client_secret=secrets.get("client_secret", ""),
                endpoint=secrets.get("endpoint", ""),
            )
            azure_status = cloud_status.get("status", "").lower()
            if azure_status in ("succeeded", "running"):
                deployment.status = "active"
            elif azure_status == "not_found":
                deployment.status = "error"
    
    # Store cloud status in config
    config["cloud_status"] = cloud_status
    deployment.config = config
    flag_modified(deployment, "config")
    await db.flush()
    
    return {
        "deployment_id": str(deployment_id),
        "status": deployment.status,
        "cloud_status": cloud_status,
    }


@router.patch("/{deployment_id}", response_model=DeploymentResponse)
async def update_deployment(
    deployment_id: UUID,
    data: DeploymentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Scale or update a deployment."""
    result = await db.execute(
        select(Deployment, CloudProvider)
        .join(CloudProvider, Deployment.provider_id == CloudProvider.id)
        .where(Deployment.id == deployment_id, Deployment.org_id == user.org_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Deployment not found")
    
    deployment, provider = row
    secrets = await _get_provider_secrets(str(provider.id))
    config = deployment.config or {}
    cloud_resource_id = config.get("cloud_resource_id", "")
    
    # Handle scaling
    if data.config and provider.provider_type == "aws" and "model_units" in data.config:
        if cloud_resource_id:
            scale_result = await scale_aws_deployment(
                cloud_resource_id=cloud_resource_id,
                new_model_units=data.config["model_units"],
                access_key_id=secrets.get("access_key_id", ""),
                secret_access_key=secrets.get("secret_access_key", ""),
                region=secrets.get("region", "us-east-1"),
            )
            if not scale_result.success:
                raise HTTPException(422, scale_result.message)
    
    elif data.config and provider.provider_type == "azure" and "tpm" in data.config:
        deployment_name = cloud_resource_id or config.get("name", "")
        if deployment_name:
            scale_result = await deploy_azure(
                model_id=config.get("cloud_model_id", ""),
                config={**config, **data.config, "name": deployment_name},
                tenant_id=secrets.get("tenant_id", ""),
                client_id=secrets.get("client_id", ""),
                client_secret=secrets.get("client_secret", ""),
                endpoint=secrets.get("endpoint", ""),
            )
            if not scale_result.success:
                raise HTTPException(422, scale_result.message)
    
    if data.config is not None:
        deployment.config = {**config, **data.config}
        flag_modified(deployment, "config")
    if data.status is not None:
        deployment.status = data.status
    
    await db.flush()
    await db.refresh(deployment)
    return deployment


@router.delete("/{deployment_id}", status_code=204)
async def delete_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete deployment — also removes cloud resources."""
    result = await db.execute(
        select(Deployment, CloudProvider)
        .join(CloudProvider, Deployment.provider_id == CloudProvider.id)
        .where(Deployment.id == deployment_id, Deployment.org_id == user.org_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Deployment not found")
    
    deployment, provider = row
    secrets = await _get_provider_secrets(str(provider.id))
    config = deployment.config or {}
    cloud_resource_id = config.get("cloud_resource_id", "")
    
    # Delete cloud resource
    if cloud_resource_id:
        if provider.provider_type == "aws":
            del_result = await delete_aws_deployment(
                cloud_resource_id=cloud_resource_id,
                access_key_id=secrets.get("access_key_id", ""),
                secret_access_key=secrets.get("secret_access_key", ""),
                region=secrets.get("region", "us-east-1"),
            )
            if not del_result.success:
                logger.warning(f"Failed to delete AWS resource: {del_result.message}")
        
        elif provider.provider_type == "azure":
            deployment_name = cloud_resource_id or config.get("name", "")
            del_result = await delete_azure_deployment(
                deployment_name=deployment_name,
                tenant_id=secrets.get("tenant_id", ""),
                client_id=secrets.get("client_id", ""),
                client_secret=secrets.get("client_secret", ""),
                endpoint=secrets.get("endpoint", ""),
            )
            if not del_result.success:
                logger.warning(f"Failed to delete Azure resource: {del_result.message}")
    
    await db.delete(deployment)
