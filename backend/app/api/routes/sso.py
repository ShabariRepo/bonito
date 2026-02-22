"""SAML SSO authentication routes.

Public endpoints for SAML authentication flow:
- SP metadata (for IdP configuration)
- Login initiation (redirects to IdP)
- Assertion Consumer Service (processes IdP response)
- Single Logout
"""

import uuid
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis_lib

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.services import saml_service, auth_service
from app.schemas.sso import SSOLoginCheckRequest, SSOStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/saml", tags=["sso"])

# Frontend URL for the SSO callback
FRONTEND_URL = settings.cors_origins.split(",")[0].strip() if settings.cors_origins else "http://localhost:3000"


def _build_request_data(request: Request, post_data: dict = None) -> dict:
    """Extract request metadata for python3-saml."""
    # Use X-Forwarded headers if behind a proxy (Railway, etc.)
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost"))

    return {
        "url": str(request.url),
        "scheme": scheme,
        "host": host,
        "get_data": dict(request.query_params),
        "post_data": post_data or {},
    }


@router.get("/{org_id}/metadata", response_class=Response)
async def sp_metadata(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return Service Provider (SP) metadata XML.
    
    This is a public endpoint — IdP admins paste this URL into their
    SAML app configuration to import SP settings automatically.
    """
    sso_config = await saml_service.get_sso_config(db, org_id)
    if not sso_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not configured for this organization")

    try:
        metadata_xml = saml_service.get_sp_metadata(sso_config)
    except Exception as e:
        logger.error("Failed to generate SP metadata for org %s: %s", org_id, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate metadata")

    return Response(content=metadata_xml, media_type="application/xml")


@router.get("/{org_id}/login")
async def saml_login(
    org_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Initiate SAML login flow — redirects the user to the IdP.
    
    The frontend navigates to this URL, which generates a SAML AuthnRequest
    and redirects the browser to the IdP's SSO endpoint.
    """
    sso_config = await saml_service.get_sso_config(db, org_id)
    if not sso_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not configured for this organization")
    if not sso_config.enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SSO is not enabled for this organization")

    request_data = _build_request_data(request)
    
    try:
        redirect_url = saml_service.initiate_saml_login(sso_config, request_data)
    except Exception as e:
        logger.error("Failed to initiate SAML login for org %s: %s", org_id, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to initiate SSO login")

    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/{org_id}/acs")
async def assertion_consumer_service(
    org_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    r: redis_lib.Redis = Depends(get_redis),
):
    """Assertion Consumer Service (ACS) — processes the SAML response from the IdP.
    
    This endpoint receives a POST from the IdP (browser redirect with SAML response).
    It validates the assertion, extracts user info, links/creates the user,
    generates JWT tokens, and redirects to the frontend callback URL.
    
    Tokens are passed in the URL fragment (hash) rather than query parameters
    for security — fragments are not sent to the server in subsequent requests.
    """
    sso_config = await saml_service.get_sso_config(db, org_id)
    if not sso_config:
        return _sso_error_redirect("SSO not configured for this organization")
    if not sso_config.enabled:
        return _sso_error_redirect("SSO is not enabled for this organization")

    # Parse the POST form data
    form_data = await request.form()
    post_data = {key: value for key, value in form_data.items()}
    
    request_data = _build_request_data(request, post_data)

    try:
        # Validate SAML response and extract attributes
        saml_attributes = await saml_service.process_saml_response(
            sso_config, request_data, r
        )
    except ValueError as e:
        logger.warning("SAML response validation failed for org %s: %s", org_id, e)
        return _sso_error_redirect(str(e))
    except Exception as e:
        logger.error("Unexpected error processing SAML response for org %s: %s", org_id, e)
        return _sso_error_redirect("Failed to process SSO response")

    try:
        # Link or create the user
        user = await saml_service.link_or_create_user(
            db, org_id, saml_attributes, sso_config.role_mapping
        )
    except ValueError as e:
        logger.warning("User provisioning failed for org %s: %s", org_id, e)
        return _sso_error_redirect(str(e))
    except Exception as e:
        logger.error("Unexpected error provisioning user for org %s: %s", org_id, e)
        return _sso_error_redirect("Failed to provision user account")

    # Generate JWT tokens
    access_token = auth_service.create_access_token(str(user.id), str(user.org_id), user.role)
    refresh_token = auth_service.create_refresh_token(str(user.id))
    await auth_service.store_session(r, str(user.id), refresh_token)

    # Redirect to frontend callback with tokens in URL fragment
    callback_url = f"{FRONTEND_URL}/auth/sso/callback#access_token={access_token}&refresh_token={refresh_token}"
    return RedirectResponse(url=callback_url, status_code=302)


@router.get("/{org_id}/slo")
async def single_logout(
    org_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    r: redis_lib.Redis = Depends(get_redis),
):
    """Single Logout (SLO) — handles IdP-initiated logout.
    
    When the IdP sends a logout request, this endpoint invalidates
    the user's session and redirects to the frontend login page.
    """
    sso_config = await saml_service.get_sso_config(db, org_id)
    if not sso_config:
        return RedirectResponse(url=f"{FRONTEND_URL}/login", status_code=302)

    # For now, just redirect to the frontend login page
    # A full SLO implementation would validate the LogoutRequest
    # and send a LogoutResponse back to the IdP
    return RedirectResponse(url=f"{FRONTEND_URL}/login?slo=true", status_code=302)


@router.post("/check-sso", response_model=SSOStatusResponse)
async def check_sso_status(
    body: SSOLoginCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    """Check if a user's email domain has SSO configured.
    
    Used by the frontend login page to show SSO prompts. This endpoint
    deliberately reveals minimal information to avoid user enumeration.
    """
    sso_config = await saml_service.get_sso_config_by_email_domain(db, body.email)
    
    if not sso_config:
        return SSOStatusResponse(sso_enabled=False)
    
    return SSOStatusResponse(
        sso_enabled=sso_config.enabled,
        sso_enforced=sso_config.enforced,
        sso_login_url=f"/api/auth/saml/{sso_config.org_id}/login" if sso_config.enabled else None,
        provider_type=sso_config.provider_type,
    )


def _sso_error_redirect(error_message: str) -> RedirectResponse:
    """Redirect to the frontend with an SSO error message."""
    encoded_error = urlencode({"error": error_message})
    return RedirectResponse(
        url=f"{FRONTEND_URL}/auth/sso/callback?{encoded_error}",
        status_code=302,
    )
