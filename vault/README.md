# Vault — Production Setup (Railway)

## Architecture

- **Storage**: File backend at `/vault/data` (Railway persistent volume)
- **Auto-unseal**: Entrypoint script unseals on every restart using `VAULT_UNSEAL_KEY`
- **KV Engine**: `secret/` mount (KV v2) — matches backend `VAULT_MOUNT=secret`

## First Deploy

1. **Create the Vault service on Railway** from the `vault/` directory
2. **Add a persistent volume** mounted at `/vault/data`
3. **Deploy** — Vault will initialize itself and print credentials to logs:

```
╔══════════════════════════════════════════════════════════════╗
║  🔑 SAVE THESE — ADD TO RAILWAY ENV VARS, THEN REDEPLOY   ║
╠══════════════════════════════════════════════════════════════╣
║                                                            ║
║  VAULT_UNSEAL_KEY=<base64-key>                             ║
║  VAULT_ROOT_TOKEN=<token>                                  ║
╚══════════════════════════════════════════════════════════════╝
```

4. **Copy the unseal key and root token** from the deploy logs
5. **Add Railway env vars** on the Vault service:
   - `VAULT_UNSEAL_KEY=<the key from logs>`
   - `VAULT_ROOT_TOKEN=<the token from logs>`
   - `SECRET_KEY=<your app secret key>` (for seeding)
   - `ENCRYPTION_KEY=<your app encryption key>` (for seeding)
6. **Redeploy** — Vault will auto-unseal and be ready

## Backend Config

Set these env vars on the **backend** service:

```
VAULT_ADDR=http://vault-service.railway.internal:8200
VAULT_TOKEN=<root token from step 4>
VAULT_MOUNT=secret
```

## Subsequent Restarts

The entrypoint handles everything automatically:
1. Starts Vault server (file storage persists across restarts)
2. Checks if sealed → auto-unseals with `VAULT_UNSEAL_KEY`
3. Ensures `secret/` KV v2 engine is enabled
4. Seeds app secrets if missing

## Local Development

Local dev uses `docker-compose.yml` which runs Vault in **dev mode** (in-memory, auto-unsealed, token: `bonito-dev-token`). This is intentional — dev doesn't need persistence.

## Security Notes

- Unseal key in env var is a trade-off: simpler ops vs. lower security
- For higher security, use cloud auto-unseal (AWS KMS, Azure Key Vault, GCP KMS)
- The backend also stores encrypted credentials in PostgreSQL as a fallback
- File storage is single-node; for HA, consider Vault with Consul or Raft backend
