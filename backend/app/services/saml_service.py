"""SAML SSO service using python3-saml (OneLogin).

Handles SAML AuthnRequest generation, response validation, and user
provisioning (JIT — Just-In-Time) for SAML-authenticated users.
"""

import uuid
import logging
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils
import redis.asyncio as redis_lib

from app.core.config import settings
from app.models.sso_config import SSOConfig
from app.models.user import User
from app.services import auth_service

logger = logging.getLogger(__name__)

# Default attribute mappings per provider
DEFAULT_ATTRIBUTE_MAPPINGS = {
    "okta": {
        "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        "name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
        "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
        "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
        "groups": "http://schemas.xmlsoap.org/claims/Group",
    },
    "azure_ad": {
        "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        "name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
        "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
        "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
        "groups": "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups",
    },
    "google": {
        "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        "name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
        "first_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
        "last_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
        "groups": "",
    },
    "custom": {
        "email": "email",
        "name": "name",
        "first_name": "firstName",
        "last_name": "lastName",
        "groups": "groups",
    },
}

# SAML assertion replay protection: store processed assertion IDs in Redis
ASSERTION_ID_TTL = 600  # 10 minutes — assertions shouldn't be reused


async def get_sso_config(db: AsyncSession, org_id: uuid.UUID) -> Optional[SSOConfig]:
    """Fetch SSO configuration for an organization."""
    result = await db.execute(
        select(SSOConfig).where(SSOConfig.org_id == org_id)
    )
    return result.scalar_one_or_none()


async def get_sso_config_by_email_domain(db: AsyncSession, email: str) -> Optional[SSOConfig]:
    """Find an enabled SSO config matching the user's email domain.
    
    This is used on the login page to detect whether an org has SSO
    enabled and prompt the user accordingly.
    """
    domain = email.split("@")[-1].lower() if "@" in email else None
    if not domain:
        return None

    # Find users with this email domain, then check their org's SSO config
    result = await db.execute(
        select(SSOConfig)
        .join(User, User.org_id == SSOConfig.org_id)
        .where(User.email.ilike(f"%@{domain}"))
        .where(SSOConfig.enabled == True)
        .limit(1)
    )
    return result.scalar_one_or_none()


def _prepare_saml2_request(request_data: dict) -> dict:
    """Convert FastAPI/Starlette request info into python3-saml's expected format."""
    url = request_data.get("url", "")
    parsed = urlparse(url) if url else None

    return {
        "https": "on" if request_data.get("scheme") == "https" else "off",
        "http_host": request_data.get("host", "localhost"),
        "server_port": parsed.port if parsed and parsed.port else (443 if request_data.get("scheme") == "https" else 80),
        "script_name": parsed.path if parsed else "",
        "get_data": request_data.get("get_data", {}),
        "post_data": request_data.get("post_data", {}),
    }


def get_saml_settings(sso_config: SSOConfig) -> dict:
    """Build python3-saml settings dict from our SSOConfig model.
    
    See https://github.com/SAML-Toolkits/python3-saml for schema details.
    """
    return {
        "strict": True,
        "debug": not settings.production_mode,
        "sp": {
            "entityId": sso_config.sp_entity_id,
            "assertionConsumerService": {
                "url": sso_config.sp_acs_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        },
        "idp": {
            "entityId": sso_config.idp_entity_id or "",
            "singleSignOnService": {
                "url": sso_config.idp_sso_url or "",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": sso_config.idp_certificate or "",
        },
        "security": {
            "nameIdEncrypted": False,
            "authnRequestsSigned": False,
            "logoutRequestSigned": False,
            "logoutResponseSigned": False,
            "signMetadata": False,
            "wantMessagesSigned": True,
            "wantAssertionsSigned": True,
            "wantNameIdEncrypted": False,
            "wantAssertionsEncrypted": False,
            # Allow 2 minutes of clock skew between SP and IdP
            "rejectedTimes": 120,
            "relaxDestinationValidation": True,
        },
    }


def initiate_saml_login(sso_config: SSOConfig, request_data: dict) -> str:
    """Generate a SAML AuthnRequest and return the IdP redirect URL.
    
    Args:
        sso_config: The org's SSO configuration
        request_data: Dict with url, scheme, host, get_data keys
        
    Returns:
        The IdP SSO URL with the SAML request parameters
    """
    saml_settings = get_saml_settings(sso_config)
    req = _prepare_saml2_request(request_data)
    auth = OneLogin_Saml2_Auth(req, saml_settings)
    return auth.login()


def get_sp_metadata(sso_config: SSOConfig) -> str:
    """Generate SP metadata XML for the IdP admin to import.
    
    Returns:
        XML string containing SP metadata
    """
    saml_settings = get_saml_settings(sso_config)
    # Use a dummy request to initialize the auth object
    dummy_req = {
        "https": "on",
        "http_host": "localhost",
        "server_port": 443,
        "script_name": "",
        "get_data": {},
        "post_data": {},
    }
    auth = OneLogin_Saml2_Auth(dummy_req, saml_settings)
    metadata = auth.get_settings().get_sp_metadata()
    errors = auth.get_settings().validate_metadata(metadata)
    if errors:
        logger.warning("SP metadata validation warnings: %s", errors)
    return metadata.decode("utf-8") if isinstance(metadata, bytes) else metadata


async def process_saml_response(
    sso_config: SSOConfig,
    request_data: dict,
    redis_client: redis_lib.Redis,
) -> dict:
    """Validate a SAML assertion and extract user attributes.
    
    Args:
        sso_config: The org's SSO configuration
        request_data: Dict with url, scheme, host, post_data keys
        redis_client: Redis client for assertion replay protection
        
    Returns:
        Dict with extracted user attributes (email, name, groups, etc.)
        
    Raises:
        ValueError: If the SAML response is invalid
    """
    saml_settings = get_saml_settings(sso_config)
    req = _prepare_saml2_request(request_data)
    auth = OneLogin_Saml2_Auth(req, saml_settings)
    
    auth.process_response()
    errors = auth.get_errors()
    
    if errors:
        error_reason = auth.get_last_error_reason()
        logger.error("SAML response validation failed: %s — %s", errors, error_reason)
        raise ValueError(f"SAML validation failed: {', '.join(errors)}. {error_reason or ''}")

    if not auth.is_authenticated():
        raise ValueError("SAML authentication failed: user not authenticated")

    # Replay protection: check if we've seen this assertion ID before
    assertion_id = auth.get_last_assertion_id()
    if assertion_id:
        replay_key = f"saml:assertion:{assertion_id}"
        already_seen = await redis_client.get(replay_key)
        if already_seen:
            raise ValueError("SAML assertion replay detected")
        await redis_client.set(replay_key, "1", ex=ASSERTION_ID_TTL)

    # Extract attributes using the configured mapping
    attr_mapping = sso_config.attribute_mapping or DEFAULT_ATTRIBUTE_MAPPINGS.get(
        sso_config.provider_type, DEFAULT_ATTRIBUTE_MAPPINGS["custom"]
    )
    
    raw_attrs = auth.get_attributes()
    name_id = auth.get_nameid()
    
    logger.info("SAML attributes received: %s, NameID: %s", list(raw_attrs.keys()), name_id)
    
    def _get_attr(key: str) -> Optional[str]:
        """Get a single attribute value, trying the mapped key first."""
        mapped_key = attr_mapping.get(key, key)
        if not mapped_key:
            return None
        values = raw_attrs.get(mapped_key, [])
        return values[0] if values else None
    
    def _get_attr_list(key: str) -> list[str]:
        """Get a list attribute value (e.g., groups)."""
        mapped_key = attr_mapping.get(key, key)
        if not mapped_key:
            return []
        return raw_attrs.get(mapped_key, [])

    email = _get_attr("email") or name_id
    first_name = _get_attr("first_name") or ""
    last_name = _get_attr("last_name") or ""
    name = _get_attr("name") or f"{first_name} {last_name}".strip() or email.split("@")[0]
    groups = _get_attr_list("groups")

    if not email or "@" not in email:
        raise ValueError("SAML response missing valid email address")

    return {
        "email": email.lower().strip(),
        "name": name,
        "first_name": first_name,
        "last_name": last_name,
        "groups": groups,
        "name_id": name_id,
        "session_index": auth.get_session_index(),
    }


async def link_or_create_user(
    db: AsyncSession,
    org_id: uuid.UUID,
    saml_attributes: dict,
    role_mapping: Optional[dict] = None,
) -> User:
    """Find an existing user by email or create a new one (JIT provisioning).
    
    If the user exists in a different org, this is an error (email uniqueness).
    If the user exists in the same org, update their name and role.
    If the user doesn't exist, create them with SSO-derived attributes.
    
    Args:
        db: Database session
        org_id: Organization ID
        saml_attributes: Dict from process_saml_response
        role_mapping: Optional dict mapping IdP groups to Bonito roles
        
    Returns:
        The User object (existing or newly created)
    """
    email = saml_attributes["email"]
    name = saml_attributes["name"]
    groups = saml_attributes.get("groups", [])
    
    # Determine role from group mapping
    role = _map_role(groups, role_mapping)
    
    # Look up existing user
    existing_user = await auth_service.get_user_by_email(db, email)
    
    if existing_user:
        if str(existing_user.org_id) != str(org_id):
            raise ValueError(f"User {email} belongs to a different organization")
        
        # Update name if provided by IdP
        if name and name != existing_user.name:
            existing_user.name = name
        
        # Update role if IdP provides groups and we have a mapping
        if groups and role_mapping and role != "viewer":
            existing_user.role = role
        
        # Mark email as verified (IdP has verified it)
        existing_user.email_verified = True
        
        await db.flush()
        return existing_user
    
    # JIT: Create new user (no password — SSO only)
    new_user = User(
        email=email,
        hashed_password=None,  # SSO users don't have passwords
        name=name,
        org_id=org_id,
        role=role,
        email_verified=True,  # IdP has verified the email
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    
    logger.info("JIT provisioned user %s (role=%s) for org %s", email, role, org_id)
    return new_user


def _map_role(groups: list[str], role_mapping: Optional[dict]) -> str:
    """Map IdP groups to a Bonito role.
    
    Checks groups against role_mapping. If multiple groups match,
    the highest-privilege role wins (admin > member > viewer).
    Falls back to "default" key in mapping, then "viewer".
    """
    if not role_mapping or not groups:
        default = (role_mapping or {}).get("default", "viewer")
        return default if default in ("admin", "member", "viewer") else "viewer"
    
    role_priority = {"admin": 3, "member": 2, "viewer": 1}
    best_role = None
    best_priority = 0
    
    for group in groups:
        mapped = role_mapping.get(group)
        if mapped and mapped in role_priority:
            if role_priority[mapped] > best_priority:
                best_role = mapped
                best_priority = role_priority[mapped]
    
    if best_role:
        return best_role
    
    # Fall back to default
    default = role_mapping.get("default", "viewer")
    return default if default in ("admin", "member", "viewer") else "viewer"
