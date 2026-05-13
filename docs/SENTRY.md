# Sentry Integration — Bonito

## Overview

Sentry provides error tracking, performance monitoring, and profiling for both the backend (FastAPI) and frontend (Next.js). Long-term, the Sentry MCP server will feed into Helios for agentic self-healing.

## Projects

| Project | Platform | Status | DSN Location |
|---------|----------|--------|--------------|
| bonito-backend | FastAPI (Python) | **Done** | `SENTRY_DSN` env var |
| bonito-frontend | Next.js | **Done** | `NEXT_PUBLIC_SENTRY_DSN` env var |

## Backend Setup (Complete)

- **SDK:** `sentry-sdk[fastapi]` in `requirements.txt`
- **Init:** `backend/app/main.py` — initializes before FastAPI app creation
- **Config:** `SENTRY_DSN` env var → `settings.sentry_dsn`
- **Sampling (prod):** 20% traces, 10% profiling
- **Sampling (dev):** 100% traces, 100% profiling
- **DSN:** Set `SENTRY_DSN` on Railway

## Frontend Setup (Complete)

- [x] Created Sentry project via API (`javascript-nextjs` platform)
- [x] Installed `@sentry/nextjs` SDK
- [x] `sentry.client.config.ts` — client-side init with Replay integration
- [x] `sentry.server.config.ts` — server-side init
- [x] `sentry.edge.config.ts` — edge runtime init
- [x] `src/instrumentation.ts` — Next.js instrumentation hook
- [x] `src/app/global-error.tsx` — error boundary that reports to Sentry
- [x] `next.config.js` — wrapped with `withSentryConfig` (source maps, org/project set)
- [x] DSN configured as `NEXT_PUBLIC_SENTRY_DSN` env var
- [ ] Set `NEXT_PUBLIC_SENTRY_DSN` on Vercel
- [ ] Set `SENTRY_AUTH_TOKEN` on Vercel (org:ci token for source maps)
- [ ] Verify error capture in production

## Helios Integration (Done)

Sentry issues are now ingested directly into Helios via the Sentry REST API collector (`helios/bonito-healer/internal/sentry/collector.go`). This replaces the MCP approach with a native Go client for better reliability.

- [x] Sentry REST API collector (`internal/sentry/collector.go`)
- [x] Config: `sentry` section in `monitor.yaml` (auth_token, org, projects, poll_interval)
- [x] Wired into Helios engine alongside GCS reader
- [x] Sentry issues mapped to `gcs.Event` format → fingerprinting → alert rules → fix pipeline
- [x] Auth token needs `project:read`, `event:read` scopes (personal token)

### How it works

1. Collector polls `GET /api/0/projects/{org}/{project}/issues/?query=is:unresolved` every 60s
2. For new/updated issues, fetches latest event via `GET /api/0/issues/{id}/events/latest/`
3. Converts Sentry issue+event → `gcs.Event` (Helios common format)
4. Feeds into `engine.HandleEvent()` → fingerprint → alert rules → fix pipeline
5. If an alert rule with `heal_action: "analyze_and_fix"` matches → Kimi → Claude → PR

### Config (in Helios `monitor.yaml`)
```yaml
sentry:
  enabled: true
  auth_token: "sntryu_..."
  org: "bonito-ai"
  projects:
    - "python-fastapi"
    - "bonito-frontend"
  poll_interval: 60s
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
