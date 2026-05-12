# Bonito Codebase Architectural Patterns

## 1. API Routes Structure (Backend)

### Key Pattern Files
- `/Users/appa/Desktop/code/bonito/backend/app/api/routes/providers.py` - Provider management
- `/Users/appa/Desktop/code/bonito/backend/app/api/routes/knowledge_base.py` - Knowledge base RAG
- `/Users/appa/Desktop/code/bonito/backend/app/api/routes/gateway.py` - API gateway proxy
- `/Users/appa/Desktop/code/bonito/backend/app/api/routes/bonobot_agents.py` - Agent execution

### Authentication Pattern
```python
# Dependency injection via fastapi.Depends
from app.api.dependencies import get_current_user

@router.get("/endpoint")
async def my_endpoint(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # User is JWT-authenticated dashboard user
    # Check org_id isolation: user.org_id
```
- Uses JWT bearer tokens decoded in `get_current_user()`
- For gateway API: separate bearer scheme with `bn-` prefix keys
- All endpoints validate user.org_id for multi-tenancy

### Error Handling
```python
raise HTTPException(status_code=404, detail="Resource not found")
raise HTTPException(status_code=422, detail="Validation error")
raise HTTPException(status_code=403, detail="Not a member of this organization")
```
- HTTPException with appropriate status codes
- Detailed error messages for API consumers
- 422 used for validation errors (Pydantic compatible)

### Vault Client Usage
```python
from app.core.vault import vault_client

# Get provider credentials from Vault
secrets = await vault_client.get_secrets(f"providers/{provider_id}")
# secrets is a dict: {"api_key": "...", "region": "..."}

# Store credentials in Vault
await store_credentials_in_vault(str(provider_id), merged_credentials)
```
- Vault stores sensitive data like API keys, credentials
- Path pattern: `providers/{provider_id}` for cloud provider creds
- Fallback: encrypted DB column if Vault unavailable
- Cache invalidation: `vault_client._cache.pop(path, None)`

### Database Access Pattern
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Query pattern
result = await db.execute(
    select(CloudProvider).where(
        and_(
            CloudProvider.id == provider_id,
            CloudProvider.org_id == user.org_id
        )
    )
)
provider = result.scalar_one_or_none()

# Flush vs commit
await db.flush()  # Within transaction, no autocommit
await db.commit() # After all changes done

# Relationships eager loading
selectinload(Agent.mcp_servers)
```

---

## 2. CLI Commands Structure

### Key Pattern Files
- `/Users/appa/Desktop/code/bonito/cli/bonito_cli/commands/providers.py` - Provider CLI
- `/Users/appa/Desktop/code/bonito/cli/bonito_cli/commands/deploy.py` - Deploy from bonito.yaml
- `/Users/appa/Desktop/code/bonito/cli/bonito_cli/commands/gateway.py` - Gateway CLI
- `/Users/appa/Desktop/code/bonito/cli/bonito_cli/api.py` - API client

### Typer Command Structure
```python
import typer
from rich.console import Console
from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.display import print_error, print_success

console = Console()
app = typer.Typer(help="Feature description")

@app.command("subcommand")
def command_name(
    arg: str = typer.Argument(..., help="Required arg"),
    opt: str = typer.Option("default", "--opt", help="Optional flag"),
    json_output: bool = typer.Option(False, "--json"),
):
    """Docstring shown in help."""
    ensure_authenticated()  # Check auth before API calls
    
    try:
        result = api.post("/endpoint", {"key": "value"})
        if json_output:
            import json
            console.print_json(json.dumps(result, default=str))
        else:
            print_success("Operation successful")
    except APIError as exc:
        print_error(f"Failed: {exc}")
```

### API Client Pattern
```python
from ..api import api, APIError

# GET
providers = api.get("/providers/")

# POST
result = api.post("/providers/connect", {
    "provider_type": "aws",
    "credentials": {"access_key_id": "...", "secret_access_key": "..."}
})

# PUT/PATCH
updated = api.put(f"/providers/{id}", {...})

# Error handling
try:
    api.get("/endpoint")
except APIError as exc:
    exc.status_code  # e.g., 404, 422, 409
    str(exc)  # error message
```

### Display Patterns
```python
from ..utils.display import (
    print_success, print_error, print_warning, print_info,
    print_table, print_dict_as_table, get_output_format
)

fmt = get_output_format(json_output)  # Returns "json" or "table"

# Rich console status
with console.status("[cyan]Loading...[/cyan]"):
    data = api.get("/endpoint")

# Pretty tables
rows = [{"Name": "...", "Status": "..."}, ...]
print_table(rows, title="My Table")
```

---

## 3. Vault Client Usage

### Pattern Location
- `/Users/appa/Desktop/code/bonito/backend/app/core/vault.py`

### Core Methods
```python
from app.core.vault import vault_client

# Get all secrets at a path (returns dict)
secrets = await vault_client.get_secrets("providers/{provider_id}")
# Returns: {"api_key": "...", "region": "...", ...}

# Get single secret value
api_key = await vault_client.get_secret("path", "key_name", default="fallback")

# Write secrets
success = await vault_client.put_secrets("path", {"key": "value"})

# Health check
health = await vault_client.health_check()
# Returns: {"status": "healthy", "code": 200}
```

### Real-World Examples

**Provider credentials storage:**
```python
# In providers route (line 229-230)
await store_credentials_in_vault(str(provider_id), merged_credentials)

# Reading back (line 135-138)
secrets = await vault_client.get_secrets(f"providers/{provider_id}")
masked_creds = mask_credentials(provider.provider_type, secrets)
```

**Configuration:**
- Vault address: `VAULT_ADDR` env (default: `http://vault:8200`)
- Token: `VAULT_TOKEN` env (default: `bonito-dev-token`)
- Mount: `VAULT_MOUNT` env (default: `secret`)

### Error Handling
```python
try:
    secrets = await vault_client.get_secrets(f"providers/{provider_id}")
except Exception as e:
    logger.warning(f"Vault failed, using DB fallback: {e}")
    # Fallback to encrypted DB column
```

---

## 4. Deploy.py YAML Parsing

### Key Pattern File
- `/Users/appa/Desktop/code/bonito/cli/bonito_cli/commands/deploy.py`

### YAML Structure
```yaml
version: "1.0"
name: "my-deployment"
description: "Deployment description"

gateway:
  providers:
    - name: aws
      api_key: ${AWS_API_KEY}  # env var interpolation
      region: us-east-1

mcp_servers:
  server_name:
    type: http
    url: http://...

knowledge_bases:
  kb_name:
    description: "KB description"
    embedding:
      model: auto
    chunking:
      max_chunk_size: 512
      overlap: 50
    sources:
      - type: directory
        path: ./docs
        glob: "**/*.md"

agents:
  agent_name:
    system_prompt: "You are a helpful agent"
    system_prompt_file: ./system_prompt.txt  # Or file reference
    model: auto  # YAML uses "model"; deploy.py maps this to "model_id" in the API payload
    knowledge_base_ids: ["kb_name"]
    max_turns: 25
```

### Processing Pipeline
```python
# 1. Load and validate YAML
cfg = yaml.safe_load(Path("bonito.yaml").read_text())
errors = _validate(cfg)  # Returns list of validation errors

# 2. Resolve env vars
cfg = _resolve_env(cfg)  # Replaces ${VAR} with os.environ values
unresolved = _find_unresolved(cfg)  # Lists ${VAR} not in environment

# 3. Read system prompt from file if ref
if isinstance(agent_cfg["system_prompt"], str) and not ref.startswith("..."):
    prompt = _read_system_prompt(agent_cfg["system_prompt_file"], yaml_dir)

# 4. Deploy sections in order
_deploy_providers(cfg.get("gateway", {}).get("providers"), result, dry_run)
project_id = _find_or_create_project(cfg["name"], verbose)
kb_id_map = _deploy_knowledge_bases(cfg.get("knowledge_bases"), ...)
_deploy_agents(cfg.get("agents"), project_id, kb_id_map, ...)
```

### Key Validation
```python
_REQUIRED_TOP_KEYS = {"version", "name"}
_KNOWN_TOP_KEYS = {"version", "name", "description", "gateway", "mcp_servers",
                   "knowledge_bases", "agents", "observability"}

# Validates:
# - All required keys present
# - agents, mcp_servers, knowledge_bases are dicts
# - Each agent has system_prompt and model
```

---

## 5. Gateway Service & Agent Execution

### Key Pattern Files
- `/Users/appa/Desktop/code/bonito/backend/app/services/gateway.py` - LiteLLM wrapper
- `/Users/appa/Desktop/code/bonito/backend/app/api/routes/gateway.py` - Gateway routes
- `/Users/appa/Desktop/code/bonito/backend/app/api/routes/bonobot_agents.py` - Agent CRUD/execution
- `/Users/appa/Desktop/code/bonito/backend/app/services/agent_engine.py` - Agent runtime

### Gateway Service Pattern
```python
from app.services import gateway as gateway_service
from app.core.vault import vault_client

# Validate API key (bn- prefix)
key = await gateway_service.validate_api_key(db, raw_key)

# Models are configured in LiteLLM
# Providers credentials loaded from Vault per provider_id
# Format: provider_type/model_id (e.g., "bedrock/claude-3-opus")

# Model aliases for version compatibility
aliases = _generate_model_aliases("gemini-2.0-flash-001")
# Returns: ["gemini-2.0-flash"]
```

### Agent Execution Pattern
```python
from app.services.agent_engine import AgentEngine

agent_engine = AgentEngine()

# Execute agent
@router.post("/projects/{project_id}/agents/{agent_id}/execute")
async def execute_agent(
    agent_id: UUID,
    request: AgentExecuteRequest,  # {"message": "user message"} — extra=forbid, unknown fields return 422
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 1. Load agent from DB
    agent = await db.get(Agent, agent_id)
    
    # 2. Create session
    session = AgentSession(agent_id=agent_id, status="running")
    db.add(session)
    await db.flush()
    
    # 3. Execute
    result = await agent_engine.run(agent, request.input, session)
    
    # 4. Save messages and results
    return AgentExecuteResponse(output=result)
```

### Agent Configuration Storage (DB Model)
```python
# From Agent model (backend/app/models/agent.py)
class Agent:
    system_prompt: str  # Agent personality/instructions
    model_id: str  # "auto" for smart routing, or specific model
    model_config: dict  # {"temperature": 0.7, "max_tokens": 2048}
    knowledge_base_ids: list  # IDs of KBs this agent can access
    tool_policy: dict  # {"mode": "none|all|allowlist|denylist", "allowed": [...], "denied": [...], "http_allowlist": [...]}
    max_turns: int  # Max tool call loops
    timeout_seconds: int  # Execution timeout
```

---

## 6. Database Models Structure

### Key Pattern File
- `/Users/appa/Desktop/code/bonito/backend/app/models/`

### Base Model Pattern
```python
# All models inherit from Base in app.core.database
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.core.database import Base

class MyModel(Base):
    __tablename__ = "my_models"
    
    # Primary key (UUID)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    
    # Foreign keys with cascade
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # String fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Text (for longer content)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # JSON columns (flexible config)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    organization = relationship("Organization", back_populates="my_models")
```

### Multi-Tenancy Pattern
```python
# EVERY table has org_id foreign key
org_id: Mapped[uuid.UUID] = mapped_column(
    ForeignKey("organizations.id", ondelete="CASCADE"),
    nullable=False
)

# ALL queries filter by org_id
result = await db.execute(
    select(MyModel).where(
        and_(
            MyModel.id == resource_id,
            MyModel.org_id == user.org_id  # Always filter org
        )
    )
)
```

### Complex Models

**CloudProvider (credentials storage):**
```python
id: Mapped[uuid.UUID]
org_id: Mapped[uuid.UUID]
provider_type: Mapped[str]  # "aws", "azure", "gcp", "openai", etc.
credentials_encrypted: Mapped[str]  # Encrypted blob or Vault reference
status: Mapped[str]  # "pending", "active", "error"
is_managed: Mapped[bool]  # For managed inference mode
```

**Agent (execution config):**
```python
system_prompt: Mapped[str]  # The agent's instructions
model_id: Mapped[str]  # "auto" or specific model
model_config: Mapped[dict]  # {"temperature": 0.7, ...}
knowledge_base_ids: Mapped[list]  # JSON array of KB UUIDs
tool_policy: Mapped[dict]  # {"mode": "none|all|allowlist|denylist", "allowed": [...], "denied": [...], "http_allowlist": [...]}
max_turns: Mapped[int]  # Max tool loop iterations
```

**KnowledgeBase (RAG system):**
```python
source_type: Mapped[str]  # "upload", "s3", "azure_blob", "gcs"
source_config: Mapped[dict]  # Cloud storage config
embedding_model: Mapped[str]  # Model for embeddings
embedding_dimensions: Mapped[int]  # e.g., 768, 1536
chunk_size: Mapped[int]  # Characters per chunk
status: Mapped[str]  # "pending", "syncing", "ready"
document_count: Mapped[int]  # Cached count
chunk_count: Mapped[int]  # Total chunks
```

---

## 7. Alembic Migrations Structure

### Key Pattern File
- `/Users/appa/Desktop/code/bonito/backend/alembic/versions/017_add_knowledge_base_tables.py`

### Migration Template
```python
"""Add knowledge base tables and enable pgvector extension

Revision ID: 017_add_knowledge_base_tables
Revises: 016_fix_key_prefix
Create Date: 2026-02-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "017_add_knowledge_base_tables"
down_revision = "016_fix_key_prefix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable PostgreSQL extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Create new tables
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        # ... more columns
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("org_id", "name", name="uq_knowledge_bases_org_name"),
    )
    
    # Create indexes
    op.create_index("ix_knowledge_bases_org_id", "knowledge_bases", ["org_id"])
    
    # Modify existing tables
    op.add_column("agents", sa.Column("new_field", sa.String(), nullable=True))
    op.create_foreign_key("fk_name", "table1", "table2", ["col1"], ["col2"])


def downgrade() -> None:
    op.drop_table("knowledge_bases")
    op.drop_column("agents", "new_field")
    op.execute("DROP EXTENSION IF EXISTS vector")
```

### Migration Patterns
- **UUID primary keys:** All use `sa.UUID()` with `default=uuid.uuid4`
- **Org isolation:** Always add `org_id` FK with `ondelete="CASCADE"`
- **Timestamps:** `server_default=sa.func.now()` for created_at
- **Status fields:** String columns with specific enum values
- **JSON config:** For flexible/nested data
- **Indexes:** Created for org_id and frequently queried fields
- **Unique constraints:** Enforce uniqueness within org (e.g., `uq_knowledge_bases_org_name`)

### Running Migrations
```bash
# In backend/ directory
alembic upgrade head    # Apply all pending
alembic downgrade -1    # Rollback one
alembic current         # Show current revision
```

---

## Summary of Key Patterns to Follow

### Authentication & Authorization
1. Use `Depends(get_current_user)` for JWT-protected endpoints
2. Always validate `user.org_id` matches resource org_id
3. Feature gates via `feature_gate.require_feature()` for premium features

### Error Handling
1. Raise `HTTPException` with appropriate status codes
2. Log warnings/errors with `logger.warning()` for non-critical failures
3. Provide detailed error messages for API consumers

### Database Access
1. Use async/await with SQLAlchemy Core patterns
2. Always wrap in transactions with `await db.flush()` before refresh
3. Filter all queries by `user.org_id` for multi-tenancy
4. Use `selectinload()` for eager relationship loading

### Credentials Management
1. Store sensitive data in Vault, not database
2. Keep encrypted fallback in DB (`credentials_encrypted` column)
3. Mask credentials in API responses
4. Use service functions: `store_credentials_in_vault()`, `mask_credentials()`

### CLI Commands
1. Use Typer decorators for subcommands
2. Call `ensure_authenticated()` before API access
3. Use Rich for formatted output (tables, panels, JSON)
4. Handle `APIError` exceptions with user-friendly messages

### Deployment
1. Parse bonito.yaml with env var interpolation: `${ENV_VAR}`
2. Validate all required fields before deployment
3. Create/reuse projects and knowledge bases atomically
4. Support dry-run mode for previewing changes

### Migrations
1. Increment revision ID (format: `###_descriptive_name` or UUID)
2. Always include `down_revision` and `revision` fields
3. Create indexes for foreign keys and commonly filtered columns
4. Use `ondelete="CASCADE"` for org-dependent resources
