# Bonito Codebase Patterns - Index

This directory contains comprehensive documentation of the Bonito codebase architectural patterns and best practices.

## Documentation Files

### 1. ARCHITECTURAL_PATTERNS.md
**Comprehensive reference guide (580 lines)**

The main documentation file with in-depth explanations of 7 architectural patterns:

1. **API Routes Structure** - FastAPI endpoints with JWT auth and multi-tenancy
   - Authentication patterns with `Depends(get_current_user)`
   - Error handling with HTTPException
   - Database access patterns with SQLAlchemy async
   - Vault client integration for secrets management
   
2. **CLI Commands Structure** - Typer + Rich-based command-line interface
   - Command structure with decorators
   - API client usage patterns
   - Display formatting (tables, JSON output)

3. **Vault Client Usage** - HashiCorp Vault for secrets management
   - Reading/writing secrets
   - Fallback to encrypted DB columns
   - Cache management and error handling

4. **Deploy.py YAML Parsing** - Infrastructure-as-code deployment
   - bonito.yaml structure and validation
   - Environment variable interpolation
   - Deployment pipeline (providers -> projects -> KBs -> agents)

5. **Gateway Service & Agent Execution** - Multi-provider routing and agent runtime
   - LiteLLM integration for model routing
   - Agent configuration and execution
   - Model aliasing and cross-provider failover

6. **Database Models Structure** - SQLAlchemy ORM patterns
   - Base model pattern with UUID PKs
   - Multi-tenancy via org_id isolation
   - Key models: CloudProvider, Agent, KnowledgeBase

7. **Alembic Migrations** - Database schema versioning
   - Migration template with upgrade/downgrade
   - Key patterns: UUIDs, org_id foreign keys, indexes
   - Running migrations

**Use this file when:**
- Learning the architecture in detail
- Implementing complex features
- Understanding design decisions
- Reference exact line numbers from actual code

### 2. PATTERNS_QUICK_REFERENCE.md
**Quick lookup guide with copy-paste templates (449 lines)**

Practical templates and quick lookups:

- **File Locations Cheat Sheet** - Where to find key files
- **Copy-Paste Code Templates** - Ready-to-use patterns for:
  - New API routes
  - New database models
  - Alembic migrations
  - CLI commands
  - Vault secrets management
  
- **Common Database Queries** - Copy-paste snippets:
  - Filtering by org_id
  - Create/Read/Update/Delete
  - List with ordering
  - Count queries
  - Eager loading relationships

- **HTTP Status Codes** - Quick reference table
- **Testing Endpoints** - curl examples and CLI usage
- **Environment Variables** - Backend and CLI configuration
- **Debugging Tips** - Common debugging strategies

**Use this file when:**
- Creating new features quickly
- Need code templates
- Looking up common patterns
- Quick reference during development

### 3. PATTERNS_INDEX.md
**This file - navigation guide**

High-level overview of the documentation structure and how to use it.

---

## Quick Navigation

### By Use Case

**"I need to add a new API endpoint"**
1. Start: PATTERNS_QUICK_REFERENCE.md -> "Copy-Paste Patterns" -> "New API Route"
2. Deep dive: ARCHITECTURAL_PATTERNS.md -> Section 1 "API Routes Structure"
3. Reference file: backend/app/api/routes/providers.py

**"I need to add a database model"**
1. Start: PATTERNS_QUICK_REFERENCE.md -> "Copy-Paste Patterns" -> "New Database Model"
2. Deep dive: ARCHITECTURAL_PATTERNS.md -> Section 6 "Database Models Structure"
3. Reference file: backend/app/models/agent.py

**"I need to create a migration"**
1. Start: PATTERNS_QUICK_REFERENCE.md -> "Copy-Paste Patterns" -> "Alembic Migration"
2. Deep dive: ARCHITECTURAL_PATTERNS.md -> Section 7 "Alembic Migrations"
3. Reference file: backend/alembic/versions/017_add_knowledge_base_tables.py

**"I need to add a CLI command"**
1. Start: PATTERNS_QUICK_REFERENCE.md -> "Copy-Paste Patterns" -> "New CLI Command"
2. Deep dive: ARCHITECTURAL_PATTERNS.md -> Section 2 "CLI Commands Structure"
3. Reference file: cli/bonito_cli/commands/providers.py

**"I need to work with secrets/Vault"**
1. Start: PATTERNS_QUICK_REFERENCE.md -> "Copy-Paste Patterns" -> "Reading/Writing Vault"
2. Deep dive: ARCHITECTURAL_PATTERNS.md -> Section 3 "Vault Client Usage"
3. Reference file: backend/app/core/vault.py

**"I need to deploy with bonito.yaml"**
1. Start: PATTERNS_QUICK_REFERENCE.md -> "Testing Endpoints Locally"
2. Deep dive: ARCHITECTURAL_PATTERNS.md -> Section 4 "Deploy.py YAML Parsing"
3. Reference file: cli/bonito_cli/commands/deploy.py

---

## Key Files to Follow

### Backend API
- `backend/app/api/routes/providers.py` - Multi-provider credential management
- `backend/app/api/routes/knowledge_base.py` - RAG document indexing
- `backend/app/api/routes/gateway.py` - OpenAI-compatible proxy
- `backend/app/api/routes/bonobot_agents.py` - Agent CRUD & execution

### Database & Models
- `backend/app/models/agent.py` - Agent configuration schema
- `backend/app/models/cloud_provider.py` - Provider credentials storage
- `backend/app/models/knowledge_base.py` - RAG metadata
- `backend/app/core/database.py` - AsyncSession setup

### Authentication & Security
- `backend/app/api/dependencies.py` - JWT auth and feature gates
- `backend/app/core/vault.py` - Secrets management

### Migrations
- `backend/alembic/versions/017_add_knowledge_base_tables.py` - Example migration

### CLI
- `cli/bonito_cli/commands/providers.py` - Provider CLI
- `cli/bonito_cli/commands/deploy.py` - Deploy command
- `cli/bonito_cli/api.py` - HTTP API client

### Services
- `backend/app/services/gateway.py` - LiteLLM wrapper
- `backend/app/services/agent_engine.py` - Agent runtime

---

## Critical Patterns - MUST FOLLOW

### 1. Multi-Tenancy (Org Isolation)
Every database query MUST filter by `user.org_id`:
```python
select(MyModel).where(
    and_(MyModel.id == id, MyModel.org_id == user.org_id)
)
```
Forgetting this is a **data leak vulnerability**.

### 2. Authentication
Every route MUST use `Depends(get_current_user)`:
```python
async def my_route(user: User = Depends(get_current_user)):
    ...
```

### 3. Database Transactions
Use `await db.flush()` NOT `await db.commit()` in routes:
```python
db.add(resource)
await db.flush()  # Correct
await db.refresh(resource)  # Get generated IDs
```

### 4. Error Handling
Use HTTPException with proper status codes:
```python
raise HTTPException(status_code=404, detail="Not found")
raise HTTPException(status_code=403, detail="Forbidden")
raise HTTPException(status_code=422, detail="Validation error")
```

### 5. Secrets Management
Store sensitive data in Vault, NOT the database:
```python
await vault_client.put_secrets(f"providers/{id}", credentials)
# Fallback: encrypted DB column
provider.credentials_encrypted = encrypt_credentials(...)
```

### 6. Migrations
Always create migrations for schema changes:
```bash
cd backend && alembic revision --autogenerate -m "description"
```

---

## Common Questions

**Q: Where do I put new API routes?**
A: `backend/app/api/routes/` - create a new file or add to existing file. See `providers.py` for pattern.

**Q: How do I add a new database table?**
A: 
1. Create model in `backend/app/models/my_resource.py`
2. Create migration with `alembic revision --autogenerate`
3. Edit migration in `backend/alembic/versions/`

**Q: How do I handle sensitive credentials?**
A: Use Vault: `await vault_client.put_secrets(path, secrets)`. Encrypt DB fallback with `encrypt_credentials()`.

**Q: How do I require authentication?**
A: Add `user: User = Depends(get_current_user)` parameter to route.

**Q: How do I filter by organization?**
A: Always include `MyModel.org_id == user.org_id` in WHERE clause.

**Q: How do I create a new CLI command?**
A: Create file in `cli/bonito_cli/commands/` with Typer decorators. See `providers.py` for pattern.

**Q: How do I call the API from CLI?**
A: Use `api.get()`, `api.post()`, `api.put()`, `api.delete()` from the API client.

**Q: How do I format CLI output?**
A: Use Rich utilities: `print_table()`, `print_success()`, `print_error()`, `console.print_json()`.

---

## Next Steps

1. **Start here**: Read PATTERNS_QUICK_REFERENCE.md for your use case
2. **Go deeper**: Read relevant section in ARCHITECTURAL_PATTERNS.md
3. **Reference actual code**: Look at the key files listed above
4. **Implement**: Use the copy-paste templates as starting point
5. **Test**: Use the debugging tips and testing commands

---

## Contributing Updates

When you add new patterns or best practices:
1. Update ARCHITECTURAL_PATTERNS.md with detailed explanation
2. Add copy-paste template to PATTERNS_QUICK_REFERENCE.md
3. Update this index if new sections are added
4. Include actual file paths and line numbers for reference

---

Generated: 2026-04-04
Bonito Architectural Patterns Documentation
