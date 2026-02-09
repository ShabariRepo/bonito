#!/bin/sh
# Vault Production Initialization Script
# Run this ONCE when first deploying Vault, or after data loss.
# Requires: VAULT_ADDR to be set (e.g., https://vault.your-railway-app.railway.app)
#
# Usage:
#   VAULT_ADDR=http://localhost:8200 ./vault/init-prod.sh
#
# This script will:
#   1. Initialize Vault (if not already initialized)
#   2. Unseal Vault (requires unseal keys)
#   3. Enable the bonito KV v2 engine
#   4. Seed secret paths (empty — you fill in real values after)

set -e

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
export VAULT_ADDR

echo "🔐 Bonito Vault Production Initialization"
echo "   Vault address: $VAULT_ADDR"
echo ""

# ── Step 1: Check if Vault is already initialized ──────────────
INIT_STATUS=$(vault status -format=json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('initialized', False))" 2>/dev/null || echo "unknown")

if [ "$INIT_STATUS" = "False" ] || [ "$INIT_STATUS" = "unknown" ]; then
    echo "⏳ Initializing Vault (1 key, threshold 1 for simplicity)..."
    echo "   ⚠️  For real production, use -key-shares=5 -key-threshold=3"
    
    vault operator init \
        -key-shares=1 \
        -key-threshold=1 \
        -format=json > /tmp/vault-init.json
    
    UNSEAL_KEY=$(cat /tmp/vault-init.json | python3 -c "import sys,json; print(json.load(sys.stdin)['unseal_keys_b64'][0])")
    ROOT_TOKEN=$(cat /tmp/vault-init.json | python3 -c "import sys,json; print(json.load(sys.stdin)['root_token'])")
    
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  🔑 SAVE THESE CREDENTIALS SECURELY — SHOWN ONLY ONCE  ║"
    echo "╠══════════════════════════════════════════════════════════╣"
    echo "║  Unseal Key:  $UNSEAL_KEY"
    echo "║  Root Token:  $ROOT_TOKEN"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
    echo "Store these in a password manager or secure location NOW."
    echo ""
    
    # Clean up
    rm -f /tmp/vault-init.json
else
    echo "✅ Vault is already initialized."
    echo ""
    echo "Enter your unseal key and root token:"
    
    if [ -z "$VAULT_UNSEAL_KEY" ]; then
        printf "   Unseal Key: "
        read -r UNSEAL_KEY
    else
        UNSEAL_KEY="$VAULT_UNSEAL_KEY"
    fi
    
    if [ -z "$VAULT_TOKEN" ]; then
        printf "   Root Token: "
        read -r ROOT_TOKEN
    else
        ROOT_TOKEN="$VAULT_TOKEN"
    fi
fi

# ── Step 2: Unseal ─────────────────────────────────────────────
SEALED=$(vault status -format=json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('sealed', True))" 2>/dev/null || echo "True")

if [ "$SEALED" = "True" ]; then
    echo "⏳ Unsealing Vault..."
    vault operator unseal "$UNSEAL_KEY"
    echo "✅ Vault unsealed."
else
    echo "✅ Vault is already unsealed."
fi

export VAULT_TOKEN="$ROOT_TOKEN"

# ── Step 3: Enable bonito KV v2 engine ─────────────────────────
echo "⏳ Enabling bonito KV v2 secrets engine..."
vault secrets enable -path=bonito kv-v2 2>/dev/null && echo "✅ Enabled." || echo "✅ Already enabled."
sleep 1

# ── Step 4: Seed secret paths with placeholders ────────────────
echo "⏳ Seeding secret paths (placeholders — fill in real values)..."

vault kv put bonito/app \
    secret_key="CHANGE-ME-GENERATE-WITH-openssl-rand-hex-32" \
    encryption_key="CHANGE-ME-GENERATE-WITH-openssl-rand-hex-32"

vault kv put bonito/api \
    groq_api_key=""

vault kv put bonito/notion \
    api_key="" \
    page_id="" \
    changelog_id=""

vault kv put bonito/database \
    url="SET-TO-RAILWAY-DATABASE-URL" \
    username="" \
    password=""

vault kv put bonito/redis \
    url="SET-TO-RAILWAY-REDIS-URL"

vault kv put bonito/providers/aws \
    access_key_id="" \
    secret_access_key="" \
    region="us-east-1"

vault kv put bonito/providers/azure \
    tenant_id="" \
    client_id="" \
    client_secret="" \
    subscription_id=""

vault kv put bonito/providers/gcp \
    project_id="" \
    credentials_json=""

echo ""
echo "✅ Vault initialized and seeded!"
echo ""
echo "📋 Secret paths created:"
vault kv list bonito/ 2>/dev/null || true
echo ""
echo "🔑 Next steps:"
echo "  1. Store the unseal key and root token securely"
echo "  2. Fill in real secret values:"
echo "     vault kv put bonito/app secret_key=\$(openssl rand -hex 32) encryption_key=\$(openssl rand -hex 32)"
echo "     vault kv put bonito/api groq_api_key='your-key'"
echo "     vault kv put bonito/notion api_key='your-key' page_id='your-id' changelog_id='your-id'"
echo "  3. Set VAULT_TOKEN in Railway environment variables"
