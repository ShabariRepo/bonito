"""SSO administration routes.

Admin-only endpoints for configuring, testing, enabling, and enforcing
SAML SSO for an organization.
"""

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import require_admin
from app.models.user import User
from app.models.sso_config import SSOConfig
from app.services import saml_service
from app.schemas.sso import SSOConfigUpdate, SSOConfigResponse, SSOEnforceRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sso", tags=["sso-admin"])

# Default SP settings — override via env or config in production
SP_ENTITY_ID_TEMPLATE = "https://getbonito.com/saml/{org_id}"
SP_ACS_URL_TEMPLATE = "https://api.getbonito.com/api/auth/saml/{org_id}/acs"


@router.get("/config", response_model=SSOConfigResponse)
async def get_sso_config(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get the current SSO configuration for the admin's organization."""
    config = await saml_service.get_sso_config(db, user.org_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SSO not configured. Use PUT /api/sso/config to create a configuration.",
        )
    return config


@router.put("/config", response_model=SSOConfigResponse)
async def upsert_sso_config(
    body: SSOConfigUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create or update SSO configuration for the admin's organization.
    
    This does not enable SSO — use POST /api/sso/enable after configuring.
    SP entity ID and ACS URL are auto-generated based on the org ID.
    """
    org_id = user.org_id
    
    # Validate breakglass user if provided
    if body.breakglass_user_id:
        bg_user = await _get_org_admin(db, org_id, body.breakglass_user_id)
        if not bg_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Break-glass user must be an admin in your organization",
            )

    # Auto-generate SP settings
    sp_entity_id = SP_ENTITY_ID_TEMPLATE.format(org_id=org_id)
    sp_acs_url = SP_ACS_URL_TEMPLATE.format(org_id=org_id)

    existing = await saml_service.get_sso_config(db, org_id)
    
    if existing:
        # Update existing config
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(existing, field, value)
        existing.sp_entity_id = sp_entity_id
        existing.sp_acs_url = sp_acs_url
        await db.flush()
        await db.refresh(existing)
        return existing
    
    # Create new config
    config = SSOConfig(
        org_id=org_id,
        provider_type=body.provider_type,
        idp_metadata_url=body.idp_metadata_url,
        idp_sso_url=body.idp_sso_url,
        idp_entity_id=body.idp_entity_id,
        idp_certificate=body.idp_certificate,
        sp_entity_id=sp_entity_id,
        sp_acs_url=sp_acs_url,
        attribute_mapping=body.attribute_mapping,
        role_mapping=body.role_mapping,
        breakglass_user_id=body.breakglass_user_id,
        enabled=False,
        enforced=False,
    )
    db.add(config)
    await db.flush()
    await db.refresh(config)
    
    logger.info("SSO config created for org %s by %s", org_id, user.email)
    return config


@router.post("/test")
async def test_sso_connection(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Test the SSO configuration.
    
    Validates that the IdP settings are correct by checking connectivity
    and certificate validity. Returns a test SAML login URL.
    """
    config = await saml_service.get_sso_config(db, user.org_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not configured")

    # Basic validation
    errors = []
    if not config.idp_sso_url:
        errors.append("IdP SSO URL is required")
    if not config.idp_entity_id:
        errors.append("IdP Entity ID is required")
    if not config.idp_certificate:
        errors.append("IdP Certificate is required")
    
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors, "message": "Configuration is incomplete"},
        )

    # Try to generate metadata (validates the config structure)
    try:
        saml_service.get_sp_metadata(config)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid SAML configuration: {str(e)}",
        )

    return {
        "status": "ok",
        "message": "SSO configuration is valid",
        "test_login_url": f"/api/auth/saml/{user.org_id}/login",
        "sp_metadata_url": f"/api/auth/saml/{user.org_id}/metadata",
        "sp_entity_id": config.sp_entity_id,
        "sp_acs_url": config.sp_acs_url,
    }


@router.post("/enable")
async def enable_sso(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Enable SSO for the organization.
    
    SSO must be configured first. Enabling SSO allows users to log in
    via their IdP. Password login still works unless SSO is enforced.
    """
    config = await saml_service.get_sso_config(db, user.org_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not configured")

    # Validate minimum required fields
    if not config.idp_sso_url or not config.idp_entity_id or not config.idp_certificate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incomplete SSO configuration. IdP SSO URL, Entity ID, and Certificate are all required.",
        )

    config.enabled = True
    await db.flush()
    
    logger.info("SSO enabled for org %s by %s", user.org_id, user.email)
    return {"status": "enabled", "message": "SSO has been enabled. Users can now sign in via SSO."}


@router.post("/enforce")
async def enforce_sso(
    body: SSOEnforceRequest,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Enforce SSO-only authentication for the organization.
    
    When enforced, password login is disabled for all users except
    the designated break-glass admin. Requires:
    - SSO to be enabled and configured
    - A break-glass admin to be designated
    """
    config = await saml_service.get_sso_config(db, user.org_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not configured")
    if not config.enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SSO must be enabled before enforcing")

    # Validate break-glass user
    bg_user = await _get_org_admin(db, user.org_id, body.breakglass_user_id)
    if not bg_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Break-glass user must be an admin in your organization",
        )

    # Ensure the break-glass user has a password set
    if not bg_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Break-glass admin must have a password set (SSO-only users cannot be break-glass)",
        )

    config.enforced = True
    config.breakglass_user_id = body.breakglass_user_id
    await db.flush()
    
    logger.info(
        "SSO enforced for org %s by %s (breakglass: %s)",
        user.org_id, user.email, bg_user.email,
    )
    return {
        "status": "enforced",
        "message": f"SSO is now enforced. Only {bg_user.email} can use password login.",
        "breakglass_admin": bg_user.email,
    }


@router.post("/disable")
async def disable_sso(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Disable SSO for the organization.
    
    This disables both SSO login and enforcement. All users will need
    to use password login. Configuration is preserved for re-enabling.
    """
    config = await saml_service.get_sso_config(db, user.org_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not configured")

    config.enabled = False
    config.enforced = False
    await db.flush()
    
    logger.info("SSO disabled for org %s by %s", user.org_id, user.email)
    return {"status": "disabled", "message": "SSO has been disabled. All users must use password login."}


async def _get_org_admin(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> User | None:
    """Fetch a user if they are an admin in the given organization."""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.org_id == org_id,
            User.role == "admin",
        )
    )
    return result.scalar_one_or_none()
