"""
Org Secrets API Routes

Generic key-value secret store scoped to each organization.
For storing non-provider secrets like Meta API tokens, DV360 credentials, webhook keys, etc.
"""

import uuid
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.org_secret import OrgSecret
from app.schemas.secret import SecretCreate, SecretUpdate, SecretListItem, SecretDetail
from app.api.dependencies import get_current_user
from app.models.user import User
from app.core.vault import vault_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/secrets", tags=["secrets"])


def _vault_path(org_id: uuid.UUID, secret_name: str) -> str:
    """Generate vault path for an org secret."""
    return f"orgs/{org_id}/secrets/{secret_name}"


@router.post("", response_model=SecretListItem, status_code=201)
async def create_secret(
    secret: SecretCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Create a new org secret.

    Secret value is stored in Vault, metadata in Postgres.
    """
    # Check if secret already exists
    result = await db.execute(
        select(OrgSecret).where(
            OrgSecret.org_id == user.org_id,
            OrgSecret.name == secret.name
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"Secret '{secret.name}' already exists")

    # Store value in Vault
    vault_path = _vault_path(user.org_id, secret.name)
    try:
        await vault_client.put_secrets(vault_path, {"value": secret.value})
    except Exception as e:
        logger.error(f"Failed to store secret in Vault: {e}")
        raise HTTPException(status_code=500, detail="Failed to store secret in Vault")

    # Store metadata in Postgres
    org_secret = OrgSecret(
        org_id=user.org_id,
        name=secret.name,
        description=secret.description,
        vault_ref=vault_path
    )
    db.add(org_secret)
    await db.flush()
    await db.refresh(org_secret)

    return SecretListItem(
        name=org_secret.name,
        description=org_secret.description,
        created_at=org_secret.created_at,
        updated_at=org_secret.updated_at
    )


@router.get("", response_model=List[SecretListItem])
async def list_secrets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    List all org secrets (metadata only, no values).
    """
    result = await db.execute(
        select(OrgSecret)
        .where(OrgSecret.org_id == user.org_id)
        .order_by(OrgSecret.created_at.desc())
    )
    secrets = result.scalars().all()

    return [
        SecretListItem(
            name=s.name,
            description=s.description,
            created_at=s.created_at,
            updated_at=s.updated_at
        )
        for s in secrets
    ]


@router.get("/{name}", response_model=SecretDetail)
async def get_secret(
    name: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get a specific secret including its value.
    """
    # Get metadata from Postgres
    result = await db.execute(
        select(OrgSecret).where(
            OrgSecret.org_id == user.org_id,
            OrgSecret.name == name
        )
    )
    org_secret = result.scalar_one_or_none()
    if not org_secret:
        raise HTTPException(status_code=404, detail=f"Secret '{name}' not found")

    # Get value from Vault
    try:
        vault_data = await vault_client.get_secrets(org_secret.vault_ref)
        value = vault_data.get("value", "")
    except Exception as e:
        logger.error(f"Failed to retrieve secret from Vault: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve secret from Vault")

    return SecretDetail(
        name=org_secret.name,
        value=value,
        description=org_secret.description,
        created_at=org_secret.created_at,
        updated_at=org_secret.updated_at
    )


@router.put("/{name}", response_model=SecretListItem)
async def update_secret(
    name: str,
    secret: SecretUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Update an existing secret's value and/or description.
    """
    # Get metadata from Postgres
    result = await db.execute(
        select(OrgSecret).where(
            OrgSecret.org_id == user.org_id,
            OrgSecret.name == name
        )
    )
    org_secret = result.scalar_one_or_none()
    if not org_secret:
        raise HTTPException(status_code=404, detail=f"Secret '{name}' not found")

    # Update value in Vault
    try:
        await vault_client.put_secrets(org_secret.vault_ref, {"value": secret.value})
    except Exception as e:
        logger.error(f"Failed to update secret in Vault: {e}")
        raise HTTPException(status_code=500, detail="Failed to update secret in Vault")

    # Update description in Postgres if provided
    if secret.description is not None:
        org_secret.description = secret.description
        await db.flush()
        await db.refresh(org_secret)

    return SecretListItem(
        name=org_secret.name,
        description=org_secret.description,
        created_at=org_secret.created_at,
        updated_at=org_secret.updated_at
    )


@router.delete("/{name}", status_code=204)
async def delete_secret(
    name: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Delete a secret (from both Vault and Postgres).
    """
    # Get metadata from Postgres
    result = await db.execute(
        select(OrgSecret).where(
            OrgSecret.org_id == user.org_id,
            OrgSecret.name == name
        )
    )
    org_secret = result.scalar_one_or_none()
    if not org_secret:
        raise HTTPException(status_code=404, detail=f"Secret '{name}' not found")

    # Delete from Vault
    try:
        await vault_client.delete_secret(org_secret.vault_ref)
    except Exception as e:
        logger.warning(f"Failed to delete secret from Vault (continuing anyway): {e}")

    # Delete from Postgres
    await db.delete(org_secret)
    await db.flush()

    return None
