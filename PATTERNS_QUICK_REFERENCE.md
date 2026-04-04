# Bonito Patterns Quick Reference

## File Locations Cheat Sheet

```
backend/
  app/
    api/
      routes/
        providers.py          <- Multi-provider credential management
        knowledge_base.py     <- RAG document indexing
        gateway.py            <- OpenAI-compatible proxy
        bonobot_agents.py     <- Agent CRUD & execution
      dependencies.py         <- get_current_user(), auth guards
    core/
      vault.py               <- Secrets management (HashiCorp)
      database.py            <- AsyncSession, Base class
    models/
      agent.py               <- Agent config schema
      cloud_provider.py      <- Provider credentials
      knowledge_base.py      <- RAG metadata
    services/
      gateway.py             <- LiteLLM wrapper
      agent_engine.py        <- Agent runtime
  alembic/
    versions/                <- Database migrations

cli/
  bonito_cli/
    commands/
      providers.py           <- CLI provider management
      deploy.py              <- bonito.yaml deployment
      gateway.py             <- CLI gateway commands
    api.py                   <- HTTP API client
```

---

## Copy-Paste Patterns

### 1. New API Route (FastAPI)
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.my_resource import MyResource

router = APIRouter(prefix="/my-resources", tags=["my-resources"])

@router.get("", response_model=List[MyResourceResponse])
async def list_resources(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all my resources for this org."""
    result = await db.execute(
        select(MyResource)
        .where(MyResource.org_id == user.org_id)
        .order_by(MyResource.created_at.desc())
    )
    return list(result.scalars().all())

@router.post("", response_model=MyResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(
    body: MyResourceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new resource."""
    resource = MyResource(
        org_id=user.org_id,
        **body.model_dump()
    )
    db.add(resource)
    await db.flush()
    await db.refresh(resource)
    return resource

@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a resource."""
    result = await db.execute(
        select(MyResource).where(
            and_(
                MyResource.id == resource_id,
                MyResource.org_id == user.org_id
            )
        )
    )
    resource = result.scalar_one_or_none()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    
    await db.delete(resource)
    await db.flush()
```

### 2. New Database Model
```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

class MyResource(Base):
    __tablename__ = "my_resources"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="active")
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    organization = relationship("Organization", back_populates="my_resources")
```

### 3. New Alembic Migration
```bash
# Generate migration
cd backend
alembic revision --autogenerate -m "add_my_resources_table"

# Edit alembic/versions/XXXX_add_my_resources_table.py
```

```python
"""Add my_resources table

Revision ID: 001_add_my_resources
Revises: <previous_revision>
Create Date: 2026-02-18
"""
from alembic import op
import sqlalchemy as sa

revision = "001_add_my_resources"
down_revision = "<previous_revision>"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "my_resources",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="'active'"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("org_id", "name", name="uq_my_resources_org_name"),
    )
    op.create_index("ix_my_resources_org_id", "my_resources", ["org_id"])

def downgrade() -> None:
    op.drop_table("my_resources")
```

### 4. New CLI Command
```python
# cli/bonito_cli/commands/my_resources.py
from __future__ import annotations

import typer
from rich.console import Console

from ..api import api, APIError
from ..utils.auth import ensure_authenticated
from ..utils.display import (
    get_output_format,
    print_error,
    print_success,
    print_table,
)

console = Console()
app = typer.Typer(help="Manage my resources")

@app.command("list")
def list_resources(
    json_output: bool = typer.Option(False, "--json"),
):
    """List all my resources."""
    fmt = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        with console.status("[cyan]Fetching resources…[/cyan]"):
            resources = api.get("/my-resources")
        
        if fmt == "json":
            import json
            console.print_json(json.dumps(resources, default=str))
        else:
            if not resources:
                console.print("No resources found")
                return
            
            rows = [
                {
                    "Name": r.get("name", "—"),
                    "Status": r.get("status", "—"),
                    "Created": r.get("created_at", "—"),
                }
                for r in resources
            ]
            print_table(rows, title="My Resources")
    except APIError as exc:
        print_error(f"Failed to list resources: {exc}")

@app.command("create")
def create_resource(
    name: str = typer.Argument(..., help="Resource name"),
    description: str = typer.Option(None, "--description"),
):
    """Create a new resource."""
    ensure_authenticated()
    
    try:
        with console.status("[cyan]Creating resource…[/cyan]"):
            result = api.post("/my-resources", {
                "name": name,
                "description": description,
            })
        
        print_success(f"Created: {name} ({result['id'][:8]}...)")
    except APIError as exc:
        print_error(f"Failed to create resource: {exc}")
```

### 5. Reading/Writing Vault Secrets
```python
from app.core.vault import vault_client
import logging

logger = logging.getLogger(__name__)

async def store_my_secret(resource_id: str, secrets: dict) -> None:
    """Store secrets in Vault with DB fallback."""
    try:
        await vault_client.put_secrets(f"my_resources/{resource_id}", secrets)
        logger.info(f"Stored secrets for {resource_id}")
    except Exception as e:
        logger.warning(f"Vault write failed: {e}, DB fallback will be used")

async def get_my_secret(resource_id: str) -> dict:
    """Get secrets from Vault with error handling."""
    try:
        secrets = await vault_client.get_secrets(f"my_resources/{resource_id}")
        return secrets
    except Exception as e:
        logger.warning(f"Vault read failed: {e}, using empty dict")
        return {}
```

---

## Common Queries

### Query with org_id filter
```python
result = await db.execute(
    select(MyModel).where(
        and_(
            MyModel.id == resource_id,
            MyModel.org_id == user.org_id
        )
    )
)
resource = result.scalar_one_or_none()
```

### Create and return
```python
resource = MyModel(org_id=user.org_id, **body.model_dump())
db.add(resource)
await db.flush()
await db.refresh(resource)
return resource
```

### Update and return
```python
resource.name = body.name
resource.description = body.description
resource.updated_at = datetime.now(timezone.utc)
await db.flush()
await db.refresh(resource)
return resource
```

### Delete
```python
await db.delete(resource)
await db.flush()
```

### List with ordering
```python
from sqlalchemy import desc

result = await db.execute(
    select(MyModel)
    .where(MyModel.org_id == user.org_id)
    .order_by(desc(MyModel.created_at))
)
return list(result.scalars().all())
```

### Count
```python
from sqlalchemy import func

result = await db.execute(
    select(func.count(MyModel.id))
    .where(MyModel.org_id == user.org_id)
)
count = result.scalar() or 0
```

### Relationship eager loading
```python
from sqlalchemy.orm import selectinload

result = await db.execute(
    select(Parent)
    .options(selectinload(Parent.children))
    .where(Parent.org_id == user.org_id)
)
```

---

## Status Codes Quick Ref

| Code | Usage | Example |
|------|-------|---------|
| 200 | Success (GET, PUT) | Returned data |
| 201 | Created (POST) | New resource |
| 204 | No Content (DELETE) | Successful delete |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Missing JWT |
| 403 | Forbidden | Not member of org |
| 404 | Not Found | Resource missing |
| 409 | Conflict | Duplicate name |
| 422 | Validation Error | Pydantic error |
| 500 | Server Error | Unexpected failure |

---

## Testing Endpoints Locally

```bash
# Get token (after login)
TOKEN=$(bonito auth login)

# List resources
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/my-resources

# Create resource
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "test"}' \
  http://localhost:8000/api/my-resources

# Or use CLI
bonito my-resources list
bonito my-resources create my-resource --description "desc"
```

---

## Environment Variables

### Backend (.env)
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/bonito
JWT_SECRET_KEY=your-secret-key
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=bonito-dev-token
SECRET_KEY=encryption-key-for-creds
```

### CLI (~/.bonito/config)
```bash
API_URL=http://localhost:8000/api
API_KEY=your-jwt-token  # Generated after auth login
```

---

## Debugging Tips

1. **Check logs:**
   ```bash
   docker compose logs backend
   docker compose logs vault
   ```

2. **Test Vault connection:**
   ```python
   health = await vault_client.health_check()
   print(health)
   ```

3. **Inspect database:**
   ```bash
   psql $DATABASE_URL
   SELECT * FROM my_resources WHERE org_id = 'your-org-id';
   ```

4. **Test API routes:**
   ```python
   # Add to route for debugging
   logger.warning(f"DEBUG: resource = {resource}")
   ```

5. **CLI verbose mode:**
   ```bash
   bonito --verbose command-name
   ```
