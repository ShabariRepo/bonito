#!/bin/sh
# Vault initialization script — seeds dev secrets
# In production, secrets are managed via Vault API/UI with proper auth backends

export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=bonito-dev-token

echo "⏳ Seeding Vault with dev secrets..."

# Enable KV v2 secrets engine at bonito/
vault secrets enable -path=bonito kv-v2 2>/dev/null || true

# Database credentials
vault kv put bonito/database \
  url="postgresql+asyncpg://bonito:bonito@postgres:5432/bonito" \
  username="bonito" \
  password="bonito"

# Redis
vault kv put bonito/redis \
  url="redis://redis:6379/0"

# App secrets
vault kv put bonito/app \
  secret_key="dev-secret-change-in-production" \
  jwt_algorithm="HS256" \
  jwt_expiry_minutes="1440"

# Notion integration
vault kv put bonito/integrations/notion \
  api_key="${NOTION_API_KEY:-placeholder}" \
  page_id="${NOTION_PAGE_ID:-placeholder}"

# Cloud provider credentials (placeholders for now)
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

echo "✅ Vault seeded successfully!"
echo "📋 Secrets stored at bonito/*"
vault kv list bonito/
