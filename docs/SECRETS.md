# Org Secrets Store

The Bonito Org Secrets Store provides a secure, org-scoped key-value storage system for managing non-provider credentials like Meta API tokens, DV360 keys, webhook secrets, and other sensitive values that agents need at runtime.

## Overview

**What are Org Secrets?**

Org secrets are different from cloud provider credentials (which use the dedicated provider management system). They're for:

- Third-party API tokens (Meta, Google Ads, DV360, etc.)
- Webhook signing keys
- Service account credentials
- Any custom secrets your agents need

**Security Model**

- **Vault Storage**: Secret values are stored in HashiCorp Vault, never in Postgres
- **Org Isolation**: Secrets are scoped to your organization and can't be accessed across orgs
- **Metadata Only**: The database stores only metadata (name, description, timestamps) and a Vault reference
- **Runtime Injection**: Agents automatically receive their declared secrets in the system prompt

**Vault Paths**

Secrets are stored at:
```
secret/orgs/{org_id}/secrets/{secret_name}
```

Each secret is stored as: `{"value": "<the_secret_value>"}`

---

## API Reference

All endpoints require authentication (JWT token) and are automatically scoped to your organization.

### POST /api/secrets

Create a new org secret.

**Request Body:**
```json
{
  "name": "META_ACCESS_TOKEN",
  "value": "your-secret-value",
  "description": "Meta Business API access token (optional)"
}
```

**Response:** `201 Created`
```json
{
  "name": "META_ACCESS_TOKEN",
  "description": "Meta Business API access token",
  "created_at": "2026-04-04T12:00:00Z",
  "updated_at": "2026-04-04T12:00:00Z"
}
```

**Errors:**
- `400 Bad Request` - Secret with this name already exists
- `500 Internal Server Error` - Failed to store secret in Vault

---

### GET /api/secrets

List all org secrets (metadata only, no values).

**Response:** `200 OK`
```json
[
  {
    "name": "META_ACCESS_TOKEN",
    "description": "Meta Business API access token",
    "created_at": "2026-04-04T12:00:00Z",
    "updated_at": "2026-04-04T12:00:00Z"
  },
  {
    "name": "DV360_CREDENTIALS_JSON",
    "description": "DV360 service account JSON",
    "created_at": "2026-04-04T11:00:00Z",
    "updated_at": "2026-04-04T11:00:00Z"
  }
]
```

---

### GET /api/secrets/{name}

Get a specific secret including its value.

**Response:** `200 OK`
```json
{
  "name": "META_ACCESS_TOKEN",
  "value": "your-secret-value",
  "description": "Meta Business API access token",
  "created_at": "2026-04-04T12:00:00Z",
  "updated_at": "2026-04-04T12:00:00Z"
}
```

**Errors:**
- `404 Not Found` - Secret not found

---

### PUT /api/secrets/{name}

Update an existing secret's value and/or description.

**Request Body:**
```json
{
  "value": "new-secret-value",
  "description": "Updated description (optional)"
}
```

**Response:** `200 OK`
```json
{
  "name": "META_ACCESS_TOKEN",
  "description": "Updated description",
  "created_at": "2026-04-04T12:00:00Z",
  "updated_at": "2026-04-04T14:30:00Z"
}
```

**Errors:**
- `404 Not Found` - Secret not found

---

### DELETE /api/secrets/{name}

Delete a secret (from both Vault and Postgres).

**Response:** `204 No Content`

**Errors:**
- `404 Not Found` - Secret not found

---

## CLI Reference

All CLI commands require authentication (`bonito auth login`).

### bonito secrets list

List all org secrets (metadata only).

```bash
bonito secrets list
```

**Example Output:**
```
╭──────────────── 🔐 Org Secrets ────────────────╮
│ Name                     Description    Created    │
├──────────────────────────────────────────────────┤
│ META_ACCESS_TOKEN        Meta API       2026-04-04 │
│ DV360_CREDENTIALS_JSON   DV360 creds    2026-04-04 │
╰──────────────────────────────────────────────────╯
2 secret(s)
```

**JSON Output:**
```bash
bonito secrets list --json
```

---

### bonito secrets get <name>

Retrieve a secret value.

```bash
bonito secrets get META_ACCESS_TOKEN
```

**Output:** (prints just the value for easy piping)
```
your-secret-value
```

**Use in scripts:**
```bash
export META_TOKEN=$(bonito secrets get META_ACCESS_TOKEN)
curl -H "Authorization: Bearer $META_TOKEN" https://graph.facebook.com/...
```

---

### bonito secrets set <name> <value>

Create or update a secret.

**Inline value:**
```bash
bonito secrets set META_ACCESS_TOKEN "your-token-here" --description "Meta API token"
```

**Read from file:**
```bash
bonito secrets set DV360_CREDENTIALS_JSON @credentials.json
```

The `@filepath` syntax reads the secret value from a file, useful for:
- JSON service account files
- Long tokens
- Multi-line values

**Example:**
```bash
# Store a service account JSON
bonito secrets set GCP_SA_KEY @service-account.json --description "GCP service account"

# Store an API key
bonito secrets set OPENAI_API_KEY @.env.openai --description "OpenAI API key"
```

---

### bonito secrets delete <name>

Delete a secret.

```bash
bonito secrets delete META_ACCESS_TOKEN
```

**Skip confirmation:**
```bash
bonito secrets delete META_ACCESS_TOKEN --yes
```

---

## bonito.yaml Syntax

Declare required secrets at the top level and reference them in agents.

**Example:**
```yaml
version: "1.0"
name: my-project

# Declare required secrets
secrets:
  - META_ACCESS_TOKEN
  - DV360_CREDENTIALS_JSON
  - WEBHOOK_SECRET

agents:
  meta-campaign-agent:
    system_prompt: prompts/meta-agent.md
    model: claude-sonnet-4
    secrets:
      - META_ACCESS_TOKEN

  analytics-agent:
    system_prompt: prompts/analytics.md
    model: gpt-4o
    secrets:
      - DV360_CREDENTIALS_JSON
      - WEBHOOK_SECRET
```

**Validation During Deploy:**

When you run `bonito deploy -f bonito.yaml`, the CLI will:
1. Check that all declared secrets exist in your org
2. **Warn** (but not fail) if any secrets are missing
3. Attach secrets to agents as declared

**Example Warning:**
```
⚠ Missing secrets (create with 'bonito secrets set'): META_ACCESS_TOKEN, WEBHOOK_SECRET
```

This is a warning, not an error, so your deploy will continue. You should create the missing secrets before running agents that depend on them.

---

## Agent Secret Injection

When an agent declares secrets, they are automatically injected into the agent's system prompt at runtime.

**How It Works:**

1. You declare secrets in your agent config (via YAML or API)
2. At agent execution time, Bonito resolves the secret values from Vault
3. Values are injected into the system prompt under a `## Secrets` section

**Example:**

Agent config:
```yaml
agents:
  my-agent:
    secrets:
      - META_ACCESS_TOKEN
      - DV360_API_KEY
```

Runtime system prompt (injected automatically):
```
You are a helpful assistant.

## Secrets
You have access to these secrets:
- META_ACCESS_TOKEN: EAABwzLixnjY...
- DV360_API_KEY: AIzaSyC-a_dqwq...

## Available Tools
...
```

**Security Notes:**

- Secrets are injected fresh on every agent run (not cached)
- If a secret is missing or can't be resolved, the agent continues without it (warning logged)
- Secrets are only visible to the agent at runtime, not in logs or the database

**Agent API Usage:**

Agents can reference secrets in their system prompt instructions:

```yaml
agents:
  meta-connector:
    system_prompt: |
      You are a Meta Business API connector.

      When making API calls to Meta, use the META_ACCESS_TOKEN secret provided above.

      Example:
      curl -H "Authorization: Bearer {{META_ACCESS_TOKEN}}" \
        https://graph.facebook.com/v18.0/me/adaccounts

    secrets:
      - META_ACCESS_TOKEN
```

The agent will have the actual token value in its context and can use it in tool calls.

---

## Security Best Practices

### 1. Never Commit Secrets to Git

Use the CLI or API to set secrets, never store them in YAML:

**Bad:**
```yaml
agents:
  my-agent:
    secrets:
      - META_ACCESS_TOKEN: EAABwzLixnjY...  # NEVER DO THIS
```

**Good:**
```yaml
secrets:
  - META_ACCESS_TOKEN  # Just declare the name

agents:
  my-agent:
    secrets:
      - META_ACCESS_TOKEN
```

Then set the value securely:
```bash
bonito secrets set META_ACCESS_TOKEN @.secrets/meta-token.txt
```

### 2. Rotate Secrets Regularly

Update secret values without changing agent configs:

```bash
bonito secrets set META_ACCESS_TOKEN "new-token-value"
```

All agents using that secret will automatically get the new value on their next run.

### 3. Use Descriptive Names

Use uppercase with underscores for secret names:

**Good:**
- `META_ACCESS_TOKEN`
- `DV360_SERVICE_ACCOUNT_JSON`
- `WEBHOOK_SIGNING_SECRET`

**Bad:**
- `token1`
- `secret`
- `mykey`

### 4. Audit Secret Access

Check audit logs for secret access:

```bash
bonito audit list --resource secrets
```

### 5. Limit Agent Access

Only give agents the secrets they actually need:

**Bad:**
```yaml
agents:
  simple-agent:
    secrets:
      - META_ACCESS_TOKEN
      - DV360_API_KEY
      - GOOGLE_ADS_KEY
      - TWITTER_API_SECRET
```

**Good:**
```yaml
agents:
  simple-agent:
    secrets:
      - META_ACCESS_TOKEN  # Only what this agent needs
```

---

## Common Use Cases

### 1. Third-Party API Integration

**Scenario:** Your agent needs to call the Meta Business API.

```bash
# Set the token
bonito secrets set META_ACCESS_TOKEN @meta-token.txt

# Deploy agent
cat > bonito.yaml <<EOF
version: "1.0"
name: meta-project

secrets:
  - META_ACCESS_TOKEN

agents:
  meta-agent:
    system_prompt: |
      You help users manage Meta ad campaigns.
      Use the META_ACCESS_TOKEN to make API calls.
    model: claude-sonnet-4
    secrets:
      - META_ACCESS_TOKEN
EOF

bonito deploy -f bonito.yaml
```

### 2. Webhook Verification

**Scenario:** Your agent receives webhooks that need signature verification.

```bash
# Store webhook secret
bonito secrets set WEBHOOK_SECRET "whsec_abc123..."

# Reference in agent
agents:
  webhook-handler:
    system_prompt: |
      You process incoming webhooks.
      Verify signatures using WEBHOOK_SECRET before processing.
    secrets:
      - WEBHOOK_SECRET
```

### 3. Service Account Credentials

**Scenario:** Your agent needs GCP or AWS service account JSON.

```bash
# Store service account JSON
bonito secrets set GCP_SA_JSON @service-account.json --description "GCP BigQuery access"

# Use in agent
agents:
  analytics-agent:
    secrets:
      - GCP_SA_JSON
```

---

## Troubleshooting

### Secret Not Found

**Error:** `404 Not Found`

**Cause:** Secret doesn't exist in your org.

**Fix:**
```bash
bonito secrets list  # Check what exists
bonito secrets set YOUR_SECRET_NAME "value"
```

### Vault Connection Failed

**Error:** `500 Internal Server Error - Failed to store secret in Vault`

**Cause:** Vault is unreachable or misconfigured.

**Fix:**
- Check Vault is running: `docker ps | grep vault` (local dev)
- Check `VAULT_ADDR` and `VAULT_TOKEN` environment variables
- Contact your Bonito admin

### Agent Not Receiving Secrets

**Symptom:** Agent runs but doesn't see secrets.

**Debugging:**
1. Check agent config:
   ```bash
   bonito agents get <agent-id> --json | jq '.secrets'
   ```

2. Verify secrets exist:
   ```bash
   bonito secrets list
   ```

3. Check agent execution logs for warnings:
   ```bash
   bonito agents logs <agent-id>
   ```

---

## Migration Guide

### From Environment Variables

**Before:**
```bash
export META_TOKEN="..."
bonito agents execute <id> "Run campaign"
```

**After:**
```bash
bonito secrets set META_ACCESS_TOKEN $META_TOKEN
bonito deploy -f bonito.yaml  # Secrets declared in YAML
```

### From Hardcoded Values

**Before (in agent system prompt):**
```
Use this API token: EAABwzLixnjY...
```

**After:**
```yaml
agents:
  my-agent:
    system_prompt: |
      Use the META_ACCESS_TOKEN secret for API calls.
    secrets:
      - META_ACCESS_TOKEN
```

---

## FAQ

**Q: Can I share secrets across agents?**

A: Yes! Declare the secret once and reference it in multiple agents:

```yaml
secrets:
  - SHARED_API_KEY

agents:
  agent-1:
    secrets: [SHARED_API_KEY]
  agent-2:
    secrets: [SHARED_API_KEY]
```

**Q: Are secrets encrypted at rest?**

A: Yes. Vault handles encryption at rest using AES-256-GCM.

**Q: Can I use secrets in MCP servers?**

A: Not directly. MCP servers have their own auth config. Use org secrets for agent-side API calls.

**Q: What happens if a secret is deleted while an agent is running?**

A: The agent will complete its current run with the cached secret value. Future runs will fail to resolve the secret (warning logged).

**Q: Can I export/backup secrets?**

A: You can list secret metadata, but values must be retrieved individually:

```bash
bonito secrets list --json > secrets-metadata.json
bonito secrets get SECRET_NAME > secret-value.txt  # One at a time
```

**Q: Are there rate limits on secret access?**

A: No rate limits on secret reads. They're resolved once per agent execution.

---

## Next Steps

- [VectorPack Documentation](VECTORPACK.md) - KB compression configuration
- [Agent Documentation](AGENTS.md) - Full agent feature reference
- [bonito.yaml Reference](BONITO_YAML.md) - Infrastructure-as-code syntax
