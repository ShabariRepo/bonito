# Sentry Integration — Bonito

## Overview

Sentry provides error tracking, performance monitoring, and profiling for both the backend (FastAPI) and frontend (Next.js). Long-term, the Sentry MCP server will feed into Helios for agentic self-healing.

## Projects

| Project | Platform | Status | DSN Location |
|---------|----------|--------|--------------|
| bonito-backend | FastAPI (Python) | **Done** | `SENTRY_DSN` env var |
| bonito-frontend | Next.js | **Pending** | TBD |

## Backend Setup (Complete)

- **SDK:** `sentry-sdk[fastapi]` in `requirements.txt`
- **Init:** `backend/app/main.py` — initializes before FastAPI app creation
- **Config:** `SENTRY_DSN` env var → `settings.sentry_dsn`
- **Sampling (prod):** 20% traces, 10% profiling
- **Sampling (dev):** 100% traces, 100% profiling
- **DSN:** Set `SENTRY_DSN` on Railway

## Frontend Setup (Pending)

- [ ] Create Sentry project via API (`javascript-nextjs` platform)
- [ ] Run `npx @sentry/wizard@latest -i nextjs` or manual SDK setup
- [ ] Configure DSN as `NEXT_PUBLIC_SENTRY_DSN` env var
- [ ] Add source maps upload in Vercel build
- [ ] Verify error capture

## Helios Integration (Future)

Goal: Connect Sentry MCP to Helios so errors auto-trigger the self-healing pipeline (Kimi → Claude → PR).

- [ ] Add Sentry MCP server to Helios config
- [ ] Auth token with `project:read`, `event:read`, `issue:read` scopes
- [ ] Wire `search_issues` into Helios ingestion loop
- [ ] Map Sentry issues → Helios fix pipeline

### Sentry MCP Setup (for Helios)

**Cloud (recommended):**
```json
{
  "mcpServers": {
    "sentry": {
      "url": "https://mcp.sentry.dev/sse"
    }
  }
}
```

**Self-hosted / stdio:**
```bash
npx @sentry/mcp-server@latest --access-token=SENTRY_TOKEN
```

## Environment Variables

| Variable | Service | Required | Description |
|----------|---------|----------|-------------|
| `SENTRY_DSN` | Backend (Railway) | Yes | FastAPI error tracking DSN |
| `NEXT_PUBLIC_SENTRY_DSN` | Frontend (Vercel) | Pending | Next.js error tracking DSN |
| `SENTRY_AUTH_TOKEN` | CI/CD | Pending | Source maps upload |
| `SENTRY_ORG` | CI/CD | Pending | Org slug for sentry-cli |
| `SENTRY_PROJECT` | CI/CD | Pending | Project slug for sentry-cli |

## Sentry API Reference

```bash
# Create project
POST https://sentry.io/api/0/teams/{org}/{team}/projects/
Authorization: Bearer {org-token}
{"name": "project-name", "platform": "javascript-nextjs"}

# List projects
GET https://sentry.io/api/0/organizations/{org}/projects/

# Get DSN (client keys)
GET https://sentry.io/api/0/projects/{org}/{project}/keys/
```
