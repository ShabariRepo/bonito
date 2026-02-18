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

### 5. Gateway model field showing '?'
**Date**: 2026-02-16
**Symptom**: Gateway request logs show model as '?' instead of the actual model name.
**Status**: TODO — field mapping needs updating.

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
