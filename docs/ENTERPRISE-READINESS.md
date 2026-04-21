# Enterprise Readiness — Open Issues

Last updated: 2026-04-20

## Priority 1 — Fix before enterprise deal closes

| # | Issue | Location | Impact | Effort |
|---|-------|----------|--------|--------|
| 1 | Per-org concurrency cap missing | `backend/app/services/gateway.py` | Noisy neighbor: one org saturates global 50-req limit | ~2hr |
| 2 | Gateway rate limit fails OPEN on Redis down | `backend/app/services/gateway.py:1310` | Unlimited requests when Redis is unavailable | ~30min |
| 3 | Timing attacks on token comparison | `backend/app/api/routes/auth.py:187,285,291` | Reset/verify/invite tokens use `==` not `secrets.compare_digest()` | ~15min |
| 4 | Body size limit conflict (10MB middleware vs 1MB route) | `middleware/security.py:56` vs `gateway.py:82-83` | Confusing behavior, middleware fix only half-applied | ~30min |
| 5 | SSO enforcement fails open on missing config | `backend/app/api/routes/auth.py:244-246` | Password login allowed if SSO config query fails | ~30min |

## Priority 2 — Should fix for enterprise hardening

| # | Issue | Location | Impact | Effort |
|---|-------|----------|--------|--------|
| 6 | Circuit breaker lacks observability | `gateway.py` LiteLLM Router config | No metrics/alerting when provider circuit trips | ~1hr |
| 7 | Vault cache has no TTL | `backend/app/core/vault.py:37` | Secrets never refresh without restart | ~1hr |
| 8 | Redis pool too small (20 conns) | `backend/app/core/config.py:44` | May bottleneck under high concurrency | ~15min |
| 9 | No per-account login lockout | `backend/app/api/routes/auth.py` | Per-IP rate limit only; no account-level brute force protection | ~2hr |
| 10 | No API key expiry/rotation | `backend/app/models/gateway.py` | bn- keys valid forever until manual revoke | ~3hr |

## Priority 3 — Nice to have

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 11 | Invite code weak entropy (48 bits) | `access_requests.py:67-68` | Acceptable with rate limiting but not ideal |
| 12 | No secret rotation without restart | `backend/app/core/config.py` | Requires redeploy to pick up rotated secrets |
| 13 | No concurrent index creation in migrations | `alembic/versions/017,018` | Brief table locks during embedding column changes |
| 14 | Redis client has no retry policy | `backend/app/core/redis.py` | No exponential backoff on transient failures |

## Already enterprise-grade

- DB connection pool (50/50, pre-ping, hourly recycle)
- Multi-tenancy isolation (org_id on every query, verified)
- API keys SHA256 hashed, never stored plaintext
- JWT: 30min access tokens, 7-day refresh with Redis revocation
- CORS properly restricted (not wildcarded)
- Security headers complete (HSTS, X-Frame-Options, CSP-adjacent)
- Structured JSON logging + GCS audit sink
- Health checks actively verify DB/Redis/Vault
- Audit trail for admin actions (persistent, queryable)
- SAML SSO with assertion replay protection
- Rate limiting per-endpoint with fail-closed on middleware layer
- Request ID tracing throughout stack

## Comparison with minimax scan

Minimax identified: DB pool (fixed), rate limiter fail mode (partially fixed — middleware only), body size (partially fixed), LiteLLM config (done), memwright SQLite (fixed), SSO migration (applied).

**Minimax missed:** timing attacks, gateway fail-open contradiction, SSO fail-open, Vault cache TTL, Redis pool size, per-account lockout, API key rotation.
