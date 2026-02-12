#!/bin/sh
# ─────────────────────────────────────────────────────────
# Bonito Vault Entrypoint — file-backed, auto-unseal
#
# Required env vars (set in Railway):
#   VAULT_UNSEAL_KEY  — base64 unseal key (generated on first init)
#   VAULT_ROOT_TOKEN  — root token (generated on first init)
#
# On FIRST deploy, these won't exist. The script will:
#   1. Start Vault
#   2. Initialize it (1 key share, threshold 1)
#   3. Print the unseal key + root token to logs
#   4. You copy those into Railway env vars
#   5. Redeploy — from then on, auto-unseal works
# ─────────────────────────────────────────────────────────
set -e

VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_ADDR

echo "🔐 Bonito Vault — starting in server mode (file storage)"

# Ensure data directory exists and is writable
mkdir -p /vault/data
chown -R vault:vault /vault/data 2>/dev/null || true

# ── Start Vault in the background ─────────────────────────
vault server -config=/vault/config/config.hcl &
VAULT_PID=$!

# Wait for Vault to be responsive (vault status exits non-zero when
# uninitialized or sealed, so check if it responds at all, not exit code)
echo "⏳ Waiting for Vault to start..."
for i in $(seq 1 30); do
    # vault status returns 0=unsealed, 1=error, 2=sealed — all mean "running"
    # Only a connection failure means "not ready yet"
    if vault status -format=json 2>&1 | grep -q '"initialized"'; then
        break
    fi
    sleep 1
done

# Verify Vault is actually responding
if ! vault status -format=json 2>&1 | grep -q '"initialized"'; then
    echo "❌ Vault failed to start after 30s"
    exit 1
fi

echo "✅ Vault is up"

# ── Check initialization status ───────────────────────────
STATUS_JSON=$(vault status -format=json 2>&1 || true)
INITIALIZED=$(echo "$STATUS_JSON" | sed -n 's/.*"initialized": *\([a-z]*\).*/\1/p')

echo "   Initialized: $INITIALIZED"

if [ "$INITIALIZED" = "false" ]; then
    echo ""
    echo "🆕 First run — initializing Vault..."
    
    vault operator init -key-shares=1 -key-threshold=1 -format=json > /tmp/vault-init.json
    
    # Parse JSON without jq (Alpine minimal image)
    NEW_UNSEAL_KEY=$(grep -A1 'unseal_keys_b64' /tmp/vault-init.json | tail -1 | tr -d ' ",[]')
    NEW_ROOT_TOKEN=$(grep 'root_token' /tmp/vault-init.json | tr -d ' ",' | cut -d: -f2)
    
    rm -f /tmp/vault-init.json
    
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  🔑 SAVE THESE — ADD TO RAILWAY ENV VARS, THEN REDEPLOY   ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    echo "║                                                            ║"
    echo "║  VAULT_UNSEAL_KEY=$NEW_UNSEAL_KEY"
    echo "║  VAULT_ROOT_TOKEN=$NEW_ROOT_TOKEN"
    echo "║                                                            ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Use the new keys for this session
    VAULT_UNSEAL_KEY="$NEW_UNSEAL_KEY"
    VAULT_ROOT_TOKEN="$NEW_ROOT_TOKEN"
    export VAULT_TOKEN="$NEW_ROOT_TOKEN"
fi

# ── Unseal ────────────────────────────────────────────────
STATUS_JSON=$(vault status -format=json 2>&1 || true)
SEALED=$(echo "$STATUS_JSON" | sed -n 's/.*"sealed": *\([a-z]*\).*/\1/p')

if [ "$SEALED" = "true" ]; then
    if [ -z "$VAULT_UNSEAL_KEY" ]; then
        echo "❌ Vault is sealed but VAULT_UNSEAL_KEY is not set!"
        echo "   Add VAULT_UNSEAL_KEY to your Railway env vars and redeploy."
        # Keep running so logs are visible, but Vault won't serve requests
        wait $VAULT_PID
        exit 1
    fi
    
    echo "⏳ Unsealing Vault..."
    vault operator unseal "$VAULT_UNSEAL_KEY"
    echo "✅ Vault unsealed"
fi

# ── Set root token ────────────────────────────────────────
if [ -n "$VAULT_ROOT_TOKEN" ]; then
    export VAULT_TOKEN="$VAULT_ROOT_TOKEN"
fi

# ── Enable KV v2 secrets engine ───────────────────────────
# The backend expects mount "secret" (default KV v2 path)
echo "⏳ Ensuring secrets engine is enabled..."
vault secrets enable -version=2 -path=secret kv 2>/dev/null && echo "✅ KV v2 enabled at secret/" || echo "✅ KV v2 already enabled at secret/"

# ── Seed app secrets if they don't exist ──────────────────
# Check if app secrets exist; if not, seed from env vars
APP_SECRETS=$(vault kv get -format=json secret/app 2>/dev/null || echo "")
if [ -z "$APP_SECRETS" ] || echo "$APP_SECRETS" | grep -q '"errors"'; then
    echo "⏳ Seeding app secrets from environment..."
    
    SK="${SECRET_KEY:-bonito-prod-secret-$(cat /dev/urandom | tr -dc 'a-f0-9' | fold -w 32 | head -n 1)}"
    EK="${ENCRYPTION_KEY:-bonito-prod-encrypt-$(cat /dev/urandom | tr -dc 'a-f0-9' | fold -w 32 | head -n 1)}"
    
    vault kv put secret/app \
        secret_key="$SK" \
        encryption_key="$EK"
    
    echo "✅ App secrets seeded"
fi

echo ""
echo "🐟 Vault is ready — file storage at /vault/data"
echo "   Address: $VAULT_ADDR"
echo "   UI: http://0.0.0.0:8200/ui"
echo ""

# ── Foreground — keep container alive ─────────────────────
wait $VAULT_PID
