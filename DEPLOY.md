# Bonito Production Deployment Guide

## Architecture

```
┌─────────────┐     ┌──────────────────┐
│   Vercel     │────▶│  Railway Backend  │
│  (Next.js)   │     │    (FastAPI)      │
└─────────────┘     └───────┬──────────┘
                            │
                  ┌─────────┼─────────┐
                  │         │         │
             ┌────▼──┐ ┌───▼──┐ ┌───▼───┐
             │Postgres│ │Redis │ │ Vault  │
             │Railway │ │Railway│ │Railway│
             └────────┘ └──────┘ └───────┘
```

**Dev/prod parity**: Same Docker images, same code paths. Only environment variables differ.

---

## Prerequisites

- [Railway CLI](https://docs.railway.app/develop/cli): `npm install -g @railway/cli`
- [Vercel CLI](https://vercel.com/docs/cli): `npm install -g vercel`
- GitHub repo connected to both platforms

---

## 1. Railway Setup (Backend + Postgres + Redis + Vault)

### Create the Railway Project

```bash
railway login
railway init    # creates a new project
```

### Add Services

1. **Postgres**: Railway dashboard → New → Database → PostgreSQL
2. **Redis**: Railway dashboard → New → Database → Redis
3. **Backend**: Railway dashboard → New → Service → Connect GitHub repo
   - Set root directory to `backend/`
   - Railway auto-detects `railway.json`
4. **Vault**: Railway dashboard → New → Docker Image → `hashicorp/vault:1.15`
   - Set start command: `vault server -config=/vault/config/config.hcl`
   - Mount volume at `/vault/data`
   - Upload `vault/config-prod.hcl` as `/vault/config/config.hcl`

### Backend Environment Variables

Set in Railway dashboard for the backend service:

| Variable | Value | Source |
|----------|-------|--------|
| `ENVIRONMENT` | `production` | Manual |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Railway reference (change `postgresql://` to `postgresql+asyncpg://`) |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` | Railway reference |
| `VAULT_ADDR` | `http://vault.railway.internal:8200` | Railway private networking |
| `VAULT_TOKEN` | (from Vault init) | Manual |
| `SECRET_KEY` | `openssl rand -hex 32` | Manual (fallback if Vault unavailable) |
| `ENCRYPTION_KEY` | `openssl rand -hex 32` | Manual (fallback) |
| `CORS_ORIGINS` | `https://your-app.vercel.app` | Manual |
| `GROQ_API_KEY` | Your API key | Manual |
| `NOTION_API_KEY` | Your API key | Manual |
| `NOTION_PAGE_ID` | Your page ID | Manual |
| `NOTION_CHANGELOG_ID` | Your changelog ID | Manual |
| `PORT` | `8000` | Manual |

> **Note**: Railway sets `PORT` automatically. The backend startup script uses `$PORT`.

### Database URL Fix

Railway's Postgres URL uses `postgresql://`. The backend needs `postgresql+asyncpg://`. Either:
- Set `DATABASE_URL` manually with the correct prefix, or
- Add URL rewriting in `config.py` (already handles this if you set the full URL)

---

## 2. Vercel Setup (Frontend)

### Connect Repository

```bash
cd frontend
vercel link    # connect to Vercel project
```

Or connect via Vercel dashboard → New Project → Import Git Repository.

### Environment Variables

Set in Vercel dashboard → Settings → Environment Variables:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://your-backend.up.railway.app` |
| `NEXTAUTH_URL` | `https://your-app.vercel.app` |
| `NEXTAUTH_SECRET` | `openssl rand -hex 32` |

### Vercel Settings

The `frontend/vercel.json` configures:
- Security headers (X-Content-Type-Options, X-Frame-Options, etc.)
- API rewrites to Railway backend (update the destination URL)
- Build settings

**Update `frontend/vercel.json`** rewrite destination to your Railway URL:
```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://your-backend.up.railway.app/api/:path*"
    }
  ]
}
```

---

## 3. Vault Production Initialization

**Run once** after deploying Vault on Railway:

```bash
# Port-forward to Vault (or use Railway's public URL temporarily)
export VAULT_ADDR=http://localhost:8200

# Run the init script
./vault/init-prod.sh
```

This will:
1. Initialize Vault with unseal keys
2. Unseal Vault
3. Enable the `bonito` KV v2 secrets engine
4. Seed all secret paths with placeholders

**⚠️ Save the unseal key and root token!** They're shown only once.

Then populate real secrets:
```bash
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=your-root-token

vault kv put bonito/app \
  secret_key=$(openssl rand -hex 32) \
  encryption_key=$(openssl rand -hex 32)

vault kv put bonito/api groq_api_key="your-key"

vault kv put bonito/notion \
  api_key="your-key" \
  page_id="your-id" \
  changelog_id="your-id"
```

### Vault Auto-Unseal

Vault on Railway will seal itself on restart. Options:
1. **Manual unseal** after each restart (simplest)
2. **Transit auto-unseal** with another Vault instance
3. **Cloud KMS** auto-unseal (AWS KMS, GCP KMS, Azure Key Vault)
4. **Skip Vault in prod** and use environment variables only (the backend supports this fallback)

For simplicity, **option 4 is recommended** to start — set all secrets as Railway env vars. Add Vault later when you need dynamic secrets or secret rotation.

---

## 4. Database Migrations

Migrations run automatically on every deploy via `backend/start-prod.sh`:

```bash
# The startup script runs:
python -m alembic upgrade head    # then starts uvicorn
```

### Manual Migration

```bash
# SSH into Railway backend or run locally with prod DATABASE_URL:
cd backend
alembic upgrade head        # apply all pending
alembic downgrade -1        # rollback one step
alembic history             # show migration history
```

### Creating New Migrations

```bash
cd backend
alembic revision --autogenerate -m "description of change"
# Review the generated file in alembic/versions/
# Commit and push — migrations apply on next deploy
```

---

## 5. CI/CD

### GitHub Actions (`.github/workflows/deploy.yml`)

On push to `main`:
1. Runs tests (backend + frontend)
2. Deploys backend to Railway
3. Deploys frontend to Vercel
4. Runs health checks

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `RAILWAY_TOKEN` | Railway API token (Settings → Tokens) |
| `VERCEL_TOKEN` | Vercel token (Settings → Tokens) |
| `VERCEL_ORG_ID` | From `.vercel/project.json` after `vercel link` |
| `VERCEL_PROJECT_ID` | From `.vercel/project.json` after `vercel link` |

### Required GitHub Variables

| Variable | Description |
|----------|-------------|
| `RAILWAY_BACKEND_URL` | e.g., `https://bonito-api.up.railway.app` |
| `VERCEL_FRONTEND_URL` | e.g., `https://bonito.vercel.app` |

### Manual Deploy

```bash
# Backend
cd backend && railway up --service bonito-backend

# Frontend
cd frontend && vercel --prod
```

---

## 6. Local Production Testing

Test the production config locally with `docker-compose.prod.yml`:

```bash
# Create .env.production with real values (see .env.production.example)
cp .env.production.example .env.production
# Edit .env.production...

# Run
docker compose -f docker-compose.prod.yml --env-file .env.production up --build
```

---

## 7. Rollback Procedures

### Backend (Railway)

```bash
# Railway keeps deployment history
railway rollback --service bonito-backend

# Or via dashboard: Deployments → click previous → Rollback
```

### Frontend (Vercel)

```bash
# Vercel keeps deployment history
# Dashboard: Deployments → click previous → Promote to Production
```

### Database

```bash
# Rollback one migration
cd backend
DATABASE_URL="your-prod-url" alembic downgrade -1
```

### Emergency: Revert to Previous Git Commit

```bash
git revert HEAD
git push origin main
# CI/CD will redeploy the reverted code
```

---

## 8. Monitoring & Troubleshooting

### Health Check

```bash
curl https://your-backend.up.railway.app/api/health
```

### Logs

```bash
# Railway
railway logs --service bonito-backend

# Vercel
vercel logs
```

### Common Issues

| Issue | Fix |
|-------|-----|
| `DATABASE_URL` scheme wrong | Change `postgresql://` to `postgresql+asyncpg://` |
| Vault sealed after restart | Unseal manually or switch to env var fallback |
| CORS errors | Add Vercel domain to `CORS_ORIGINS` |
| Migrations fail | Check `DATABASE_URL` is set and accessible |
| Frontend can't reach backend | Check `NEXT_PUBLIC_API_URL` and CORS settings |

---

## Secret Fallback Chain

The backend loads secrets in this order:

1. **Vault** → tries `VAULT_ADDR` + `VAULT_TOKEN`
2. **Environment variables** → `SECRET_KEY`, `ENCRYPTION_KEY`, etc.
3. **Error** (production) or **dev defaults** (development)

This means you can run production with Vault OR just env vars. Start with env vars, add Vault when ready.
