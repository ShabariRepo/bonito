#!/bin/sh
# Vault initialization script — seeds dev secrets
# In production, secrets are managed via Vault API/UI with proper auth backends

export VAULT_ADDR=http://127.0.0.1:8200
export VAULT_TOKEN=bonito-dev-token

echo "⏳ Seeding Vault with dev secrets..."

# Enable KV v2 secrets engine at bonito/
vault secrets enable -path=bonito kv-v2 2>/dev/null || true

# Wait a moment for the secrets engine to be ready
sleep 1

# App secrets (JWT, encryption, etc.)
vault kv put bonito/app \
  secret_key="dev-secret-change-in-production-12345" \
  encryption_key="dev-encryption-key-change-in-production-12345"

# API secrets (external services)
vault kv put bonito/api \
  groq_api_key="${GROQ_API_KEY:-}" 

# Notion integration
vault kv put bonito/notion \
  api_key="${NOTION_API_KEY:-}" \
  page_id="${NOTION_PAGE_ID:-}" \
  changelog_id="${NOTION_CHANGELOG_ID:-}"

# Database credentials
vault kv put bonito/database \
  url="postgresql+asyncpg://bonito:bonito@postgres:5432/bonito" \
  username="bonito" \
  password="bonito"

# Redis
vault kv put bonito/redis \
  url="redis://redis:6379/0"

# Cloud provider credentials (placeholders for production)
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
echo "📋 Available secret paths:"
vault kv list bonito/ 2>/dev/null | grep -v "Keys" | grep -v "^$" | sed 's/^/  bonito\//'

echo ""
echo "🔑 To add production secrets:"
echo "  vault kv put bonito/app secret_key='your-production-secret'"
echo "  vault kv put bonito/api groq_api_key='your-groq-api-key'"
echo "  vault kv put bonito/notion api_key='your-notion-api-key'"