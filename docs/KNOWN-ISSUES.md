# Known Issues & Troubleshooting

Tracking document for known issues, workarounds, and fixes. Useful for sales, support, and engineering.

## Resolved

### 1. `sqlalchemy.dialects:postgres` — Backend crash on Railway pgvector
**Date**: 2026-02-18
**Symptom**: Backend fails to start with `NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:postgres`
**Cause**: Railway's pgvector marketplace plugin sets `DATABASE_URL` with `postgres://` prefix instead of `postgresql://`. SQLAlchemy only recognizes `postgresql://` or `postgresql+asyncpg://`.
**Fix**: Updated `config.py` to handle both `postgres://` and `postgresql://` prefixes (commit `bab75e4`).
**Impact**: Backend was down for ~10 minutes until fix deployed.

### 2. Azure zero TPM quota in East US
**Date**: 2026-02-16
**Symptom**: Azure OpenAI model deployments failing — models show 0 TPM quota.
**Cause**: East US region had zero available TPM for all model families.
**Fix**: Created new Azure OpenAI resource `bonito-ai-eastus2` in East US 2 region which had available quota.
**Impact**: Required re-creating all Azure deployments in new region.

### 3. Azure deployment API unreliable
**Date**: 2026-02-16
**Symptom**: Data plane deployment API returning inconsistent results.
**Fix**: Switched to ARM management API (`Microsoft.CognitiveServices/accounts/deployments`) which is reliable.

### 4. Embedding model hang during KB ingestion
**Date**: 2026-02-18
**Symptom**: Document upload succeeds but processing hangs at "processing" status forever. No error. Chunks never generated.
**Cause**: `EmbeddingGenerator` tried to use `amazon.titan-embed-text-v2:0` which was in the model catalog but NOT activated on the customer's Bedrock account. LiteLLM's `router.aembedding()` call hung indefinitely with no timeout.
**Fix**:
1. Added 30-second timeout on embedding calls (fail fast instead of hanging)
2. Changed model priority to prefer serverless models (GCP `text-embedding-005`, OpenAI `text-embedding-3-small`) that don't need explicit activation
3. Clear error message when timeout occurs, directing users to model activation feature
4. Fixed pgvector column dimension mismatch (was 1536, GCP outputs 768)
**Lesson**: Always prefer serverless/always-available models for background operations. Never assume catalog presence = activated. Add timeouts to all external API calls.

### 5. pgvector CAST syntax error in vector search
**Date**: 2026-02-18
**Symptom**: KB search queries fail with SQLAlchemy parameter conflict. pgvector `::vector` cast syntax conflicts with SQLAlchemy's named parameter syntax.
**Cause**: Using `::vector` PostgreSQL cast operator in raw SQL within SQLAlchemy, which interprets `:vector` as a bind parameter.
**Fix**: Switched to explicit `CAST(... AS vector)` syntax which is SQLAlchemy-safe (commit `9bed2bc`).
**Impact**: KB search was broken until fix deployed; no data loss.

### 6. KB search response schema mismatch
**Date**: 2026-02-18
**Symptom**: KB search API returning fields that didn't match the `KBSearchResponse` Pydantic schema — frontend couldn't parse results. Missing `score`, `document_id`, `document_name`, and metadata fields.
**Cause**: Search endpoint was returning raw ORM objects instead of mapping to the response schema. Also `KBDocument.file_name` was accessed as `.name` in one code path.
**Fix**: Aligned response mapping with `KBSearchResponse` schema — explicit mapping of `score`, `document_id`, `document_name`, and metadata fields (commits `99d8b15`, `c317480`).
**Impact**: KB search results were malformed until fix; no data loss.

### 7. RAG retrieval poisoning gateway DB session
**Date**: 2026-02-18
**Symptom**: Gateway requests intermittently failing after RAG context retrieval — DB session left in bad state.
**Cause**: RAG vector search was sharing the same DB session as the main gateway transaction. If the search hit an error, it rolled back the entire gateway session.
**Fix**: RAG retrieval now uses a separate, independent DB session (commit `f53ba2b`).
**Impact**: Intermittent 500 errors on gateway requests with KB enabled.

### 8. Bonito extension field forwarded to upstream LLM
**Date**: 2026-02-18
**Symptom**: Upstream LLM providers returning 400 errors when KB-augmented requests were forwarded.
**Cause**: The `bonito` extension field in the request body (containing `knowledge_base` settings) was not being stripped before forwarding to the upstream provider.
**Fix**: Strip bonito extension field from request body before forwarding (commit `39f604b`).
**Impact**: All KB-enabled gateway requests were failing until fix.

### 9. Gateway model field showing '?'
**Date**: 2026-02-16
**Symptom**: Gateway request logs show model as '?' instead of the actual model name.
**Status**: TODO — field mapping needs updating.

### 10. Vercel: React Flow Controls style prop type error
**Date**: 2026-02-19
**Symptom**: Vercel build failed — `@xyflow/react` `<Controls>` component rejects `style` prop (typed as `CSSProperties | undefined`, not arbitrary).
**Cause**: Passing `style={{ ... }}` to `<Controls>` from `@xyflow/react` — component doesn't accept React `style` prop directly.
**Fix**: Replaced `style` prop with Tailwind child selectors (`[&>button]:!bg-gray-700` etc.) on a wrapping container (commit on `main`).

### 11. Vercel: CreateProjectData.description required vs undefined
**Date**: 2026-02-19
**Symptom**: TypeScript strict mode error — `description` field on `CreateProjectData` was typed `string` but assigned `undefined` from form state.
**Fix**: Made `description` optional (`string | undefined`) in the schema.

### 12. Vercel: useSearchParams() outside Suspense boundary
**Date**: 2026-02-19
**Symptom**: SSO callback page crashed at build time — Next.js 14 requires `useSearchParams()` to be wrapped in a `<Suspense>` boundary.
**Fix**: Split SSO callback into inner component + outer `<Suspense>` wrapper.

### 13. Railway: python3-saml native deps missing in production Docker stage
**Date**: 2026-02-19
**Symptom**: Railway build failed — `xmlsec` Python package couldn't find `libxmlsec1` headers during pip install in the production stage.
**Cause**: Dockerfile production stage only had runtime libs. `python3-saml` needs `libxmlsec1-dev`, `gcc`, `pkg-config` at install time.
**Fix**: Added `libxmlsec1-dev`, `libxmlsec1-openssl`, `gcc`, `pkg-config` to the production stage's `apt-get install`.

### 14. Railway: KnowledgeBaseChunk import renamed to KBChunk
**Date**: 2026-02-19
**Symptom**: `ImportError: cannot import name 'KnowledgeBaseChunk'` — agent engine importing old model name.
**Fix**: Changed import to `KBChunk` (the actual model class name after KB refactor). Commit `83518e2`.

### 15. Railway: Nonexistent GatewayService class in agent engine
**Date**: 2026-02-19
**Symptom**: `ImportError: cannot import name 'GatewayService'` — agent engine referenced a class that was never implemented.
**Cause**: Agent engine was designed assuming a `GatewayService` wrapper class. Actual gateway is a direct `chat_completion()` function.
**Fix**: Replaced with direct `gateway_chat_completion()` call using a separate DB session to avoid async conflicts. Created `kb_content.py` with `search_knowledge_base()` for vector search.

### 16. Railway: Alembic postgres:// URL not converted
**Date**: 2026-02-19
**Symptom**: Alembic migrations fail on Railway — `NoSuchModuleError: sqlalchemy.dialects:postgres`.
**Cause**: Railway sets `DATABASE_URL` with `postgres://` prefix. Alembic's `env.py` wasn't applying the same `postgres://` → `postgresql://` conversion that `config.py` does.
**Fix**: Added URL prefix conversion in `alembic/env.py` `run_async_migrations()`. Commit `b3a5bd4`.

### 17. Railway: get_db_session vs get_db (FastAPI dependency injection)
**Date**: 2026-02-19
**Symptom**: `TypeError: 'async_generator' object does not support the asynchronous context manager protocol` in bonobot routes.
**Cause**: Routes used `async with get_db_session()` but `get_db` is a FastAPI `Depends()` async generator, not an `@asynccontextmanager`.
**Fix**: Changed all bonobot routes to use `db: AsyncSession = Depends(get_db)` pattern. Commit `69477dc`.

### 18. Railway: Agent model_config nullable JSON .get() crash
**Date**: 2026-02-19
**Symptom**: `AttributeError: 'NoneType' object has no attribute 'get'` when agent engine reads `model_config`.
**Cause**: `model_config` is a nullable JSON column — defaults to `None` not `{}`.
**Fix**: Guard with `(agent.model_config or {}).get(...)` everywhere model_config is accessed.

### 19. Railway: AgentSession metadata column name mismatch
**Date**: 2026-02-19
**Symptom**: Pydantic validation error on `AgentSessionResponse` — field `session_metadata` not found.
**Cause**: SQLAlchemy model maps Python attribute `session_metadata` to DB column `metadata`. Pydantic schema had `session_metadata` but `model_validate()` reads from the ORM attribute.
**Fix**: Renamed DB column to `metadata` in prod, kept SQLAlchemy `mapped_column("metadata")` with Python attr `session_metadata`. Made nullable fields `Optional` in schema.

### 20. Railway: redis_client is None at import time
**Date**: 2026-02-19
**Symptom**: `AttributeError: 'NoneType' object has no attribute 'get'` on redis operations in agent execution.
**Cause**: `from app.core.redis import redis_client` captures `None` at module import. Redis client is initialized lazily.
**Fix**: Changed to `await get_redis()` at call time instead of module-level import.

### 21. Railway: greenlet_spawn error in agent engine gateway calls
**Date**: 2026-02-19
**Symptom**: `MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here` during agent execution.
**Cause**: Agent engine's `gateway_chat_completion()` used the same DB session as the route handler. SQLAlchemy async sessions can't be shared across different async contexts.
**Fix**: Created a separate `get_db_session()` (`@asynccontextmanager`) specifically for the agent engine's internal gateway calls, independent of the route's DB session. Commit `2c12b5d`.

## Open — Bonobot v1 (AI Agents)

### 22. Agent engine gateway integration — internal service call
**Date**: 2026-02-19
**Symptom**: Agent engine calls the gateway via internal service function rather than HTTP. May need adjustment depending on the gateway service interface in different deployment environments.
**Status**: Working in current architecture. Monitor when deploying to non-standard environments.

### 23. Message compaction not yet implemented
**Date**: 2026-02-19
**Symptom**: Agent sessions accumulate all messages without compaction. Long-running agent sessions will grow context windows unboundedly.
**Status**: TODO in engine (marked in code). Compaction/summarization strategy needed for sessions exceeding context limits.

### 25. GCP provider a1000004 missing project_id
**Date**: 2026-05-06
**Symptom**: `Failed to fetch gcp models (provider=a1000004-0000-0000-0000-000000000004 org=4fdadef3-16cb-4389-9f88-97ef5e5d01c7): 'project_id'` on every model sync cycle.
**Cause**: Manually inserted GCP provider record has incomplete credentials — missing `project_id` key. Not a code bug; data issue with this specific internal provider.
**Status**: Open. Need to either fix credentials in DB/Vault or deactivate the provider. Does not affect new users — the connect flow requires `project_id`.

### 26. Unknown caller polling POST /v1/chat/completions → 401 every 30s
**Date**: 2026-05-06
**Symptom**: `HTTP 401: Missing API key` + `POST /v1/chat/completions -> 401` every ~30 seconds. No API key provided.
**Cause**: Unknown. Could be a health check from Railway/Vercel, a misconfigured client, or a stale integration. No request metadata logged to identify the caller.
**Status**: Open. Not harmful (rejected at auth layer), but adds log noise. Consider logging source IP or User-Agent on 401s to identify the caller.

### 27. Gateway does not fall back to DB when Vault is unavailable
**Date**: 2026-05-06
**Symptom**: If Vault restarts or becomes unavailable, the gateway's `_get_provider_credentials()` silently skips providers instead of falling back to the encrypted DB column.
**Cause**: Gateway reads Vault directly (`vault_client.get_secrets()`) rather than using `_get_provider_secrets()` which has the Vault → DB fallback chain.
**Status**: Open. Added to roadmap in CLAUDE.md. Active PoCs are fine as long as Vault stays up.

### 24. send_notification and list_models tools are stubs
**Date**: 2026-02-19
**Symptom**: The `send_notification` and `list_models` built-in agent tools return placeholder/stub responses. They don't perform real notification delivery or dynamic model listing.
**Status**: Stubs. Will be wired to real implementations in a future iteration.

---

## Architecture Notes

### Embedding Model Selection
- **GCP Vertex AI**: `text-embedding-005` (768 dims) — serverless, always available if API enabled. **Preferred.**
- **OpenAI**: `text-embedding-3-small` (1536 dims) — serverless, needs API key
- **AWS Bedrock**: `amazon.titan-embed-text-v2:0` (1024 dims) — requires model access activation first
- **Azure**: Embedding models need explicit deployment — not suitable for auto-selection

### pgvector Configuration
- Column type: `vector(768)` (matches GCP text-embedding-005)
- Index: HNSW with cosine similarity (`vector_cosine_ops`)
- Parameters: m=16, ef_construction=64 (good balance of speed/recall for <100K vectors)

### RAG Pipeline Flow
1. Document upload → parse → chunk (512 tokens, 50 overlap)
2. Generate embeddings via org's cheapest available model (serverless preferred)
3. Store chunks + vectors in pgvector
4. At query time: embed user query → cosine similarity search → top 5 chunks
5. Inject context as system message before user's prompt
6. Route to any model (GPT-4o, Gemini, Claude) — model never touches storage directly

### 14. AWS Bedrock inference profiles — newer models fail with 403
**Date**: 2026-02-23
**Symptom**: Anthropic Claude Sonnet 4, Opus 4, Haiku 4.5, and Meta Llama 3.2+ models return `not authorized to perform: bedrock:InvokeModel on resource: arn:aws:bedrock:*:*:inference-profile/*`.
**Cause**: AWS changed how newer foundation models are invoked. Instead of calling the model ID directly, they require **cross-region inference profiles** with a `us.` prefix (e.g., `us.anthropic.claude-sonnet-4-20250514-v1:0`). These profiles have a different ARN pattern (`inference-profile/*`) that wasn't in the IAM policy.
**Fix**:
1. Backend now auto-prefixes newer Bedrock models with `us.` for inference profiles (commit `0706b08`)
2. IAM policy updated to include `arn:aws:bedrock:*:ACCOUNT_ID:inference-profile/*` resource
3. All IaC onboarding templates (Terraform, Pulumi, CloudFormation, Manual) updated with inference profile ARN
**Impact**: All newer Anthropic and Meta models on Bedrock were unusable. Older models (Nova Lite, Nova Pro) unaffected.
**Lesson**: AWS Bedrock's invocation model changed for newer models. Always include `inference-profile/*` in IAM policies alongside `foundation-model/*`. IaC templates must stay current with provider changes.

### 15. Non-chat models appearing in playground
**Date**: 2026-02-23
**Symptom**: Image/video models (Sora, DALL-E, Titan Image, Stable Diffusion) and embedding models appear in the playground model selector.
**Cause**: Model list endpoint returned all synced models without filtering by capability.
**Fix**: Added `?chat_only=true` param to model list API; backend filters out non-chat patterns (embed, sora, dall-e, image, video, tts, whisper, etc.). Playground frontend uses this param. Backend execution endpoint also rejects non-chat models with a clear error.
**Impact**: UX issue only — selecting a non-chat model would fail with a 500.

### 17. Legacy provider endpoints stored credentials as plaintext
**Date**: 2026-05-06
**Symptom**: After Railway restart, Vault loses credentials (dev-mode = in-memory). DB fallback fails with `Incorrect padding` error. Model sync logs `Failed to fetch real [provider] models: No credentials found`. Affected providers: `a1000001-a1000004` (internally created providers).
**Cause**: `POST /api/providers` and `PATCH /api/providers/{id}` legacy endpoints stored credentials via `json.dumps()` instead of `encrypt_credentials()`. The DB `credentials_encrypted` column contained plain JSON, not AES-256-GCM base64.
**Fix**:
1. Legacy endpoints now use `encrypt_credentials()` + store in Vault (PR #43031)
2. DB fallback auto-detects plain JSON, reads it, re-encrypts the row, and re-seeds Vault
3. Downgraded "No credentials" log from error to debug (expected for providers without keys)
**Impact**: Internal providers (BonBon, AI Copilot) were non-functional after Vault restarts until manual re-seeding. Now self-heals automatically.

### 18. Bedrock `get_foundation_model_availability` API does not exist
**Date**: 2026-05-06
**Symptom**: ~900 warning lines per model sync cycle: `'Bedrock' object has no attribute 'get_foundation_model_availability'`. All Bedrock models defaulted to "unavailable" status.
**Cause**: `_check_model_access()` in `aws_bedrock.py` called `get_foundation_model_availability()` which isn't a real boto3 Bedrock API method.
**Fix**: Replaced with `get_foundation_model(modelIdentifier=model_id)` which returns `modelDetails.modelLifecycle.status` (PR #43031).
**Impact**: Log noise only — models still synced but all showed "unavailable" status. Now correctly shows "available"/"unavailable" based on lifecycle.

### 19. Provider connection issues — direct API providers (Anthropic, OpenAI, Groq)
**Date**: 2026-05-06
**Symptom**: Users couldn't connect Anthropic (422 from deprecated model), Groq (422 from Pydantic regex), or any direct provider through the providers page (redirected to onboarding wizard). Connect modal also missing auth token.
**Cause**: Multiple issues:
1. Anthropic validation hardcoded `claude-3-haiku-20240307` which was deprecated
2. Onboarding `ValidateCredentialsRequest` regex only allowed `aws|azure|gcp`
3. Providers page "Connect" buttons all linked to `/onboarding` instead of opening connect modal
4. Connect modal used raw `fetch()` instead of `apiRequest()` (missing JWT)
**Fix**: PRs #43028, #43029, #43030:
1. Anthropic validation now uses `/v1/models` endpoint
2. Onboarding regex accepts all 6 providers + added `_validate_direct_api()` handler
3. Providers page buttons open ConnectModal with Groq support
4. Connect modal uses `apiRequest()` for auth
5. Background model sync (24h) keeps catalogs fresh
**Impact**: All direct API provider connections were blocked for new users.

### 16. Alembic multiple migration heads — deploy fails
**Date**: 2026-02-23
**Symptom**: Railway deploy fails with `Multiple head revisions are present for given argument 'head'` followed by `DuplicateColumn: column "subscription_tier" of relation "organizations" already exists`.
**Cause**: Two feature branches (logging system + bonobot/subscription) both forked from migration `019_add_sso_config` and added overlapping columns/tables.
**Fix**: Created alembic merge migration + made duplicate migrations idempotent (check column/table existence before CREATE).
**Impact**: Backend started but with `Migration FAILED` warning. DB was functional (columns existed from other branch).
