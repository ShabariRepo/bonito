# SSO/SAML Implementation Scoping Document

This document outlines the scope, technical approach, and effort estimates for adding Single Sign-On (SSO) support to Bonito.

## Overview

Enterprise customers require SSO for:
- **Security** — Centralized identity management, enforced MFA, automatic deprovisioning
- **Compliance** — SOC-2 and enterprise security policies typically mandate SSO
- **User experience** — One-click login via existing corporate identity

Bonito needs to support both **OIDC** (OpenID Connect) and **SAML 2.0** to cover the enterprise IdP landscape.

## Protocol Support

### Priority 1: OpenID Connect (OIDC)

OIDC is the modern standard, simpler to implement, and covers the most common enterprise IdPs.

**Supported IdPs via OIDC:**
- Google Workspace
- Microsoft Azure AD (Entra ID)
- Okta
- Auth0
- OneLogin
- Keycloak (self-hosted)

**Why OIDC first:**
- Simpler protocol (built on OAuth 2.0, JSON-based)
- Better developer experience and library support
- Covers ~70% of enterprise SSO needs
- Faster time to market

### Priority 2: SAML 2.0

SAML is older but still required by many large enterprises, especially those with legacy IdP infrastructure.

**Supported IdPs via SAML:**
- Okta
- Microsoft ADFS
- Azure AD (Entra ID)
- OneLogin
- PingFederate
- Shibboleth

**Why SAML second:**
- More complex protocol (XML-based, certificate management)
- Required for some enterprise deals but not all
- Can reference OIDC implementation patterns

## Technical Architecture

### Authentication Flow (OIDC)

```
User clicks "Sign in with SSO"
    │
    ▼
Bonito redirects to IdP authorization endpoint
    │
    ▼
User authenticates at IdP (MFA, etc.)
    │
    ▼
IdP redirects back to Bonito with authorization code
    │
    ▼
Bonito exchanges code for tokens (ID token + access token)
    │
    ▼
Bonito extracts user identity from ID token
    │
    ▼
Match/create user in Bonito database
    │
    ▼
Issue Bonito JWT session token
```

### Authentication Flow (SAML)

```
User clicks "Sign in with SSO"
    │
    ▼
Bonito generates SAML AuthnRequest, redirects to IdP
    │
    ▼
User authenticates at IdP
    │
    ▼
IdP POSTs SAML Response (signed XML assertion) to Bonito ACS URL
    │
    ▼
Bonito validates signature, extracts user identity
    │
    ▼
Match/create user in Bonito database
    │
    ▼
Issue Bonito JWT session token
```

## Backend Changes

### Libraries

| Protocol | Library | Notes |
|---|---|---|
| OIDC | **authlib** (Python) | Mature, well-maintained, supports all OIDC flows |
| SAML | **python3-saml** (OneLogin) | Most popular Python SAML library, battle-tested |

Alternative: **python-social-auth** for a higher-level abstraction (supports both OIDC and SAML), but adds complexity and may be harder to customize.

**Recommendation:** Use `authlib` for OIDC and `python3-saml` for SAML directly. More control, better debugging, fewer abstraction layers.

### Database Schema Changes

New tables/columns needed:

```sql
-- SSO configuration per organization
CREATE TABLE sso_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    protocol VARCHAR(10) NOT NULL CHECK (protocol IN ('oidc', 'saml')),
    provider_name VARCHAR(100) NOT NULL,  -- e.g., 'okta', 'azure_ad', 'google'
    
    -- OIDC fields
    oidc_client_id VARCHAR(500),
    oidc_client_secret_vault_key VARCHAR(500),  -- Reference to Vault, not plaintext
    oidc_issuer_url VARCHAR(1000),              -- e.g., https://accounts.google.com
    oidc_scopes VARCHAR(500) DEFAULT 'openid email profile',
    
    -- SAML fields
    saml_idp_entity_id VARCHAR(1000),
    saml_idp_sso_url VARCHAR(1000),
    saml_idp_certificate TEXT,          -- IdP's X.509 certificate for signature validation
    saml_sp_entity_id VARCHAR(1000),    -- Bonito's entity ID
    saml_acs_url VARCHAR(1000),         -- Assertion Consumer Service URL
    saml_name_id_format VARCHAR(200) DEFAULT 'urn:oasis:names:tc:SAML:2.0:nameid-format:emailAddress',
    
    -- Common fields
    is_active BOOLEAN DEFAULT false,
    enforce_sso BOOLEAN DEFAULT false,   -- If true, block password login for this org
    auto_provision BOOLEAN DEFAULT true, -- Auto-create users on first SSO login
    default_role VARCHAR(50) DEFAULT 'member',
    allowed_domains TEXT[],              -- Restrict SSO to specific email domains
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Link external identities to Bonito users
CREATE TABLE user_external_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    sso_config_id UUID NOT NULL REFERENCES sso_configs(id),
    external_id VARCHAR(500) NOT NULL,   -- IdP's unique identifier for the user
    external_email VARCHAR(500),
    external_name VARCHAR(500),
    last_login_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',         -- Additional claims/attributes from IdP
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(sso_config_id, external_id)
);

-- Add to existing users table
ALTER TABLE users ADD COLUMN sso_only BOOLEAN DEFAULT false;
```

### API Endpoints

```
# SSO Configuration (admin only)
POST   /api/v1/org/{org_id}/sso              -- Create SSO config
GET    /api/v1/org/{org_id}/sso              -- Get SSO config
PUT    /api/v1/org/{org_id}/sso/{config_id}  -- Update SSO config
DELETE /api/v1/org/{org_id}/sso/{config_id}  -- Delete SSO config
POST   /api/v1/org/{org_id}/sso/{config_id}/test  -- Test SSO connection

# SSO Authentication
GET    /api/v1/auth/sso/login?org={slug}     -- Initiate SSO flow
GET    /api/v1/auth/sso/callback/oidc        -- OIDC callback
POST   /api/v1/auth/sso/callback/saml        -- SAML ACS endpoint
GET    /api/v1/auth/sso/metadata/{config_id} -- SAML SP metadata XML
```

## Frontend Changes

### Login Page
- Add "Sign in with SSO" button below the existing email/password form
- SSO button prompts for organization slug/domain, then redirects to IdP
- Alternative: email-based discovery (user enters email → Bonito checks if org has SSO → redirects)

### Organization Settings Page (Admin)
- New "Single Sign-On" tab in organization settings
- Configuration form:
  - Select protocol (OIDC or SAML)
  - Protocol-specific fields (client ID, issuer URL, or IdP metadata upload)
  - Domain restrictions
  - Auto-provisioning toggle
  - Enforce SSO toggle (block password login)
  - Test connection button
- For SAML: display SP metadata URL and ACS URL for the admin to configure in their IdP

### User Profile
- Show linked external identity (if SSO user)
- If `enforce_sso` is on, hide password change option

## Implementation Plan

### Phase 1: OIDC (2–3 weeks)

| Week | Tasks |
|---|---|
| **Week 1** | Database migrations, SSO config CRUD API, authlib integration, OIDC login/callback flow |
| **Week 2** | User matching/provisioning logic, JWT issuance after SSO, frontend login changes, org settings UI |
| **Week 3** | Testing with real IdPs (Google, Azure AD, Okta), edge cases (deactivated users, domain restrictions, enforce SSO), documentation |

### Phase 2: SAML (2–3 weeks)

| Week | Tasks |
|---|---|
| **Week 4** | python3-saml integration, SAML AuthnRequest generation, ACS endpoint, signature validation |
| **Week 5** | SP metadata endpoint, IdP metadata XML import/parsing, frontend SAML config UI |
| **Week 6** | Testing with real IdPs (Okta SAML, Azure AD SAML, ADFS), certificate rotation handling, documentation |

**Total estimated effort: 4–6 weeks** for full OIDC + SAML support.

## Security Considerations

- **Client secrets** must be stored in Vault, never in the database directly
- **SAML signatures** must be validated on every assertion — no unsigned assertions
- **State parameter** (OIDC) and **RelayState** (SAML) must be validated to prevent CSRF
- **Domain validation** — only allow SSO for verified email domains
- **Account linking** — handle the case where a user already exists with email/password and later SSO is enabled
- **Session management** — SSO sessions should respect IdP session expiry (check `exp` claim)
- **Audit logging** — log all SSO events (login, failure, config changes)

## IdP-Specific Notes

### Google Workspace
- Uses OIDC exclusively
- Issuer: `https://accounts.google.com`
- Well-documented, easiest to implement first
- Supports PKCE (recommended)

### Microsoft Azure AD (Entra ID)
- Supports both OIDC and SAML
- OIDC issuer: `https://login.microsoftonline.com/{tenant}/v2.0`
- Tenant-specific configuration required
- Multi-tenant app registration possible

### Okta
- Supports both OIDC and SAML
- Well-documented developer portal
- Most common enterprise IdP we'll encounter
- Test with Okta Developer (free tier)

### OneLogin
- Supports both OIDC and SAML
- Less common but still seen in enterprise
- Good SAML implementation for testing

## Testing Strategy

- **Unit tests** for token validation, user matching, config CRUD
- **Integration tests** with mock IdP (use `authlib` test utilities or a local Keycloak instance)
- **Manual testing** with real IdPs:
  - Google Workspace (OIDC)
  - Okta Developer (OIDC + SAML)
  - Azure AD free tier (OIDC + SAML)
- **Edge cases:**
  - User exists with password, org enables SSO
  - User deactivated in IdP but active in Bonito
  - Multiple SSO configs for one org (unlikely but handle gracefully)
  - IdP certificate rotation
  - Expired/invalid SAML assertions

## Dependencies

- `authlib>=1.3.0` — OIDC client
- `python3-saml>=1.16.0` — SAML SP
- `lxml>=5.0.0` — XML processing for SAML (dependency of python3-saml)
- `xmlsec>=1.3.0` — XML signature validation

## Open Questions

1. **Should we support IdP-initiated SAML?** (IdP sends assertion without Bonito initiating the flow) — Recommendation: Not initially, add later if requested.
2. **SCIM provisioning?** (Automatic user sync from IdP) — Recommendation: Out of scope for v1, but design the schema to accommodate it later.
3. **Just-in-time provisioning vs pre-provisioning?** — Recommendation: JIT provisioning (auto-create users on first SSO login) with optional domain restriction.
4. **Pricing tier gating?** — SSO is an Enterprise feature. Enforce at the API level.

---

*Document created February 2026. Update as implementation progresses.*
