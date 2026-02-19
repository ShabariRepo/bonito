"""SSO/SAML configuration model.

Stores per-organization SAML SSO settings including IdP metadata,
attribute/role mappings, and enforcement options.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class SSOConfig(Base):
    __tablename__ = "sso_configs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # One SSO config per organization
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Provider type: okta, azure_ad, google, custom
    provider_type: Mapped[str] = mapped_column(String(50), nullable=False, default="custom")

    # Identity Provider (IdP) settings
    idp_metadata_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    idp_sso_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    idp_entity_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    idp_certificate: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Service Provider (SP) settings — auto-generated but stored for reference
    sp_entity_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sp_acs_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Attribute mapping: maps SAML assertion attributes to Bonito user fields
    # e.g. {"email": "urn:oid:0.9.2342.19200300.100.1.3", "name": "urn:oid:2.5.4.3"}
    attribute_mapping: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Role mapping: maps IdP group names to Bonito roles
    # e.g. {"Engineering": "member", "Platform Admins": "admin", "default": "viewer"}
    role_mapping: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Feature flags
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    enforced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    # Break-glass admin: this user can always log in with password even when SSO is enforced
    breakglass_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
