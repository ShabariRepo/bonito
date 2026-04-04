# Task: Org Secrets Store + VectorBoost KB Compression Config

## Overview
Two features to build on the Bonito platform. Both must be API-accessible, CLI-accessible, and declarable in bonito.yaml.

## IMPORTANT RULES
- Do NOT modify any existing test files or break existing functionality
- Do NOT touch provider_service.py vault paths -- those work fine as-is
- Follow existing code patterns exactly (look at how providers.py, knowledge_base.py, and the CLI commands are structured)
- All new API routes must require authentication (get_current_user dependency)
- Use the existing vault_client singleton from app.core.vault
- Run alembic for any DB migrations

---

## Feature 1: Org Secrets Store

### What
A generic key-value secret store scoped to each organization. For storing non-provider secrets like Meta API tokens, DV360 credentials, webhook keys, etc. that agents need at runtime.

### Vault Paths
```
secret/orgs/{org_id}/secrets/{key_name}
```
Each secret is stored as: `{"value": "<the_secret_value>"}`

### API Routes (new file: backend/app/api/routes/secrets.py)
Add to the main router in backend/app/main.py.

```
POST   /api/secrets              body: {name: str, value: str, description?: str}
GET    /api/secrets              returns: [{name, description, created_at, updated_at}] -- NO values
GET    /api/secrets/{name}       returns: {name, value, description}
PUT    /api/secrets/{name}       body: {value: str, description?: str}
DELETE /api/secrets/{name}
```

All endpoints scoped to the authenticated user's org_id automatically.

### Database Model (new file: backend/app/models/org_secret.py)
```python
class OrgSecret(Base):
    __tablename__ = "org_secrets"
    
    id: UUID (primary key, uuid4)
    org_id: UUID (FK to organizations.id, not null)
    name: str (String(255), not null)  # key name like META_ACCESS_TOKEN
    description: str (Text, nullable)
    vault_ref: str (String(512), not null)  # vault path reference
    created_at: datetime
    updated_at: datetime
    
    # Unique constraint: (org_id, name) -- one secret per name per org
```

Secret values are NEVER stored in Postgres. Only the name/metadata. Values go to Vault.

### CLI (new file: cli/bonito_cli/commands/secrets.py)
Register in cli/bonito_cli/app.py like the other commands.

```
bonito secrets set <name> <value>          # create or update
bonito secrets set <name> @<filepath>      # read value from file
bonito secrets list                        # table: name, description, created_at
bonito secrets get <name>                  # prints value
bonito secrets delete <name>               # with confirmation
```

### bonito.yaml Support
In cli/bonito_cli/commands/deploy.py, add support for a top-level `secrets:` key:

```yaml
secrets:
  - META_ACCESS_TOKEN
  - DV360_CREDENTIALS_JSON
```

During deploy, validate that all declared secrets exist (call GET /api/secrets to list names). If missing, print a warning but don't fail the deploy.

Agent references:
```yaml
agents:
  my-agent:
    secrets: [META_ACCESS_TOKEN]
```

Store the secret references on the agent record. Add a `secrets` JSON column to the agents table (nullable, default null).

### Agent Runtime Injection
In backend/app/services/gateway.py (or wherever agent execution happens), when an agent declares secrets, resolve them from Vault before execution and inject into the prompt context as `{{SECRET_NAME}}` replacements or as a `_secrets` dict available to the agent.

Look at how the existing agent execution flow works and add secret resolution there.

---

## Feature 2: VectorBoost (KB Compression Config)

### What
Per-knowledge-base compression configuration. The compression code already exists in `backend/app/services/vector_compression.py` on the current branch. This feature makes it configurable per KB via API, CLI, and yaml.

### Database
Add to the existing KnowledgeBase model (backend/app/models/knowledge_base.py):
```python
compression_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)
# Values: null/None = off, "scalar-8bit", "polar-4bit", "polar-8bit"
```

Create an alembic migration for this column.

### API
Add to the existing knowledge_base.py routes:

```
PUT  /api/kb/{kb_id}/config    body: {compression: {method: "scalar-8bit"|"polar-4bit"|"polar-8bit"|"off"}}
GET  /api/kb/{kb_id}/config    returns: {compression: {method: "...", stats: {...}}}
```

When compression method changes, it should NOT re-process existing documents automatically (that's expensive). Just store the setting -- new documents ingested after the change will use the new method.

### CLI
Add to existing cli/bonito_cli/commands/kb.py:

```
bonito kb config <kb_name_or_id> --compression scalar-8bit
bonito kb config <kb_name_or_id> --compression off
bonito kb config <kb_name_or_id>                          # show current config
```

### bonito.yaml Support
```yaml
knowledge_bases:
  my-kb:
    compression:
      method: scalar-8bit
```

During deploy, if compression is specified, call PUT /api/kb/{id}/config after KB creation.

---

## Feature 3: Documentation

### New doc: docs/SECRETS.md
- What org secrets are and why they exist (non-provider keys)
- API reference (all endpoints with examples)
- CLI reference (all commands with examples)
- bonito.yaml syntax
- Agent secret injection (how agents access secrets at runtime)
- Security model (Vault storage, org isolation, no values in Postgres)

### New doc: docs/VECTORBOOST.md
- What VectorBoost is: adaptive vector compression for KB embeddings
- Methods available:
  - `scalar-8bit`: Naive scalar quantization. 3.9x compression, 99.5% recall. Zero risk, production-ready. Recommended default.
  - `polar-4bit`: PolarQuant-inspired. Higher compression (8x), lower recall (~95%). For large KBs where storage matters more than precision.
  - `polar-8bit`: PolarQuant 8-bit. 3.9x compression, 97% recall. Slightly worse than scalar but no per-vector normalization overhead.
- Benchmark results (from the research):
  - Naive scalar 8-bit: 3.9x compression, 99.5% recall
  - PolarQuant 8-bit: 3.9x, 97% recall
  - PolarQuant Lloyd-Max 8-bit: 3.9x, 95.5% recall, best IP distortion (0.000003)
- API reference
- CLI reference
- bonito.yaml syntax
- When to use each method

### Update: docs/WALKTHROUGH.md
Add sections for both features in the appropriate places.

---

## File Inventory

### New files to create:
- backend/app/api/routes/secrets.py
- backend/app/models/org_secret.py
- cli/bonito_cli/commands/secrets.py
- docs/SECRETS.md
- docs/VECTORPACK.md
- alembic migration for org_secrets table
- alembic migration for kb compression_method column

### Files to modify:
- backend/app/main.py (register secrets router)
- backend/app/models/__init__.py (import OrgSecret)
- backend/app/models/knowledge_base.py (add compression_method column)
- backend/app/api/routes/knowledge_base.py (add config endpoints)
- backend/app/services/gateway.py or agent execution path (secret injection)
- cli/bonito_cli/app.py (register secrets command)
- cli/bonito_cli/commands/kb.py (add config subcommand)
- cli/bonito_cli/commands/deploy.py (add secrets + compression yaml support)
- docs/WALKTHROUGH.md (add sections)

### DO NOT modify:
- backend/app/core/vault.py (works fine as-is)
- backend/app/services/provider_service.py (existing provider vault paths are fine)
- Any existing test files

---

## Git Instructions
- You are on branch `experiment/polarquant-kb-compression`
- Create a new branch from this: `git checkout -b feat/secrets-and-vectorpack`
- Make all changes on that branch
- Commit with conventional commit messages (feat:, docs:, etc.)
- Do NOT push -- just commit locally
