# Bonito Roadmap

_Last updated: 2026-02-22_

## Current Status
- All 18 core phases complete ✅
- **AI Context (Knowledge Base) — SHIPPED** ✅ (cross-cloud RAG pipeline, fully E2E tested)
- **Bonobot Enterprise Features — SHIPPED** ✅ (persistent memory, scheduled execution, approval queue)
- Live at https://getbonito.com
- Backend: https://celebrated-contentment-production-0fc4.up.railway.app
- 3 cloud providers (AWS Bedrock, Azure OpenAI, GCP Vertex AI)
- 387+ models catalogued, 12 active deployments, 171+ gateway requests, $0.043 cost tracked
- PostgreSQL 18.2 with pgvector (migrated from PG17 on 2026-02-18)
- CLI tested and working against prod (25 commands, 9 bug fixes)
- E2E tested: AWS ✅, GCP ✅, Azure ✅

---

## 🔥 TOP PRIORITY: Knowledge Base — Cross-Cloud RAG ⭐⭐⭐

_Ingest once, use everywhere. Company knowledge that works with any model on any cloud._

**This is Bonito's stickiest feature and our biggest competitive moat.** No cloud provider offers cross-cloud RAG. AWS Knowledge Bases lock you to Bedrock. Azure AI Search locks you to Azure OpenAI. GCP RAG Engine locks you to Vertex. Bonito breaks that.

---

### Why This Is #1

1. **Stickiness**: Once their company docs live in Bonito, switching cost is massive
2. **Revenue multiplier**: Every knowledge-augmented query = embedding retrieval call + inference call = 2x gateway traffic
3. **Competitive gap**: LiteLLM, Portkey, Helicone — none have a knowledge layer. This is unique.
4. **Enterprise demand**: RAG is the #1 enterprise AI use case after basic chat. Every company wants "AI that knows us."
5. **Natural extension**: We already have the gateway, the model routing, the multi-cloud credentials. Knowledge is the missing piece.

---

### Architecture

```
┌─── Customer's Data (stays in their cloud) ──────────────────────┐
│  S3 Bucket / Azure Blob / GCS Bucket / Direct Upload            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Bonito reads (with IaC-provisioned permissions)
                           ▼
┌─── Bonito Ingestion Pipeline ───────────────────────────────────┐
│                                                                  │
│  1. FETCH         Pull docs from customer's storage              │
│                   (S3 API / Azure Blob API / GCS API)            │
│                                                                  │
│  2. PARSE         Extract text from files                        │
│                   PDF, DOCX, TXT, MD, HTML, CSV, JSON            │
│                   (unstructured library — no external service)    │
│                                                                  │
│  3. CHUNK         Split into retrieval-sized pieces              │
│                   - Recursive text splitter (default 512 tokens) │
│                   - Overlap 50 tokens for context continuity     │
│                   - Respect document boundaries (headers, etc.)  │
│                   - Configurable per knowledge base              │
│                                                                  │
│  4. EMBED         Generate vector embeddings                     │
│                   Routed through Bonito gateway → customer's     │
│                   own cloud (their credits, their data path)     │
│                   Default: cheapest embedding model available    │
│                   - AWS: amazon.titan-embed-text-v2              │
│                   - Azure: text-embedding-3-small                │
│                   - GCP: text-embedding-005                      │
│                                                                  │
│  5. STORE         Write vectors to pgvector                      │
│                   (PostgreSQL extension — no new infra)           │
│                   Partitioned by org_id for isolation             │
│                                                                  │
│  6. INDEX         HNSW index for fast similarity search          │
│                   Auto-reindex on threshold (>10K new chunks)     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─── Gateway Request Flow (Knowledge-Augmented) ──────────────────┐
│                                                                  │
│  Customer App                                                    │
│    │                                                             │
│    │  POST /v1/chat/completions                                  │
│    │  {                                                          │
│    │    "model": "gpt-4o",                                       │
│    │    "messages": [{"role": "user", "content": "..."}],        │
│    │    "bonito": { "knowledge_base": "hr-docs" }  ← NEW FIELD  │
│    │  }                                                          │
│    │                                                             │
│    ▼                                                             │
│  Bonito Gateway                                                  │
│    │                                                             │
│    ├─ 1. Embed the user query (→ customer's embedding model)     │
│    ├─ 2. Search pgvector for top-K relevant chunks               │
│    ├─ 3. Inject chunks into system prompt as context             │
│    ├─ 4. Route augmented prompt to best model (smart routing)    │
│    └─ 5. Return response + source citations                     │
│                                                                  │
│  Response includes:                                              │
│    - AI answer (grounded in their docs)                          │
│    - Source chunks used (file name, page, relevance score)       │
│    - Token counts (retrieval + inference)                        │
│    - Cost breakdown (embedding cost + inference cost)            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Key design decision:** Embeddings are generated through the customer's OWN cloud models via the Bonito gateway. Their data never touches a third-party embedding service. This matters for compliance.

---

### Database Schema (pgvector — no new infrastructure)

```sql
-- Enable pgvector extension (one-time)
CREATE EXTENSION IF NOT EXISTS vector;

-- Knowledge bases (one per use case per org)
CREATE TABLE knowledge_bases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Source configuration
    source_type VARCHAR(20) NOT NULL,  -- 's3', 'azure_blob', 'gcs', 'upload'
    source_config JSONB NOT NULL DEFAULT '{}',
    -- s3:         {"bucket": "...", "prefix": "hr-docs/", "region": "us-east-1"}
    -- azure_blob: {"container": "...", "prefix": "...", "account": "..."}
    -- gcs:        {"bucket": "...", "prefix": "..."}
    -- upload:     {} (files uploaded directly via API)

    -- Embedding configuration
    embedding_model VARCHAR(100) DEFAULT 'auto',  -- 'auto' = cheapest available
    embedding_dimensions INT DEFAULT 1536,
    chunk_size INT DEFAULT 512,
    chunk_overlap INT DEFAULT 50,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- pending, syncing, ready, error
    document_count INT DEFAULT 0,
    chunk_count INT DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    last_synced_at TIMESTAMPTZ,
    sync_schedule VARCHAR(50),  -- cron expression or null for manual
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(org_id, name)
);

-- Documents within a knowledge base
CREATE TABLE kb_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_base_id UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    org_id UUID NOT NULL,
    
    -- File info
    file_name VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000),  -- path in source storage
    file_type VARCHAR(20),    -- pdf, docx, txt, md, html, csv, json
    file_size BIGINT,
    file_hash VARCHAR(64),    -- SHA-256 for dedup/change detection
    
    -- Processing status
    status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, ready, error
    chunk_count INT DEFAULT 0,
    error_message TEXT,
    
    -- Metadata (customer can add tags, categories, etc.)
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vector chunks (the actual searchable pieces)
CREATE TABLE kb_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
    knowledge_base_id UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    org_id UUID NOT NULL,
    
    -- Content
    content TEXT NOT NULL,
    token_count INT,
    chunk_index INT,  -- position within document
    
    -- Vector embedding
    embedding vector(1536),  -- pgvector type, dimension matches model
    
    -- Source reference (for citations)
    source_file VARCHAR(500),
    source_page INT,
    source_section VARCHAR(500),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW index for fast similarity search
CREATE INDEX idx_kb_chunks_embedding ON kb_chunks 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Partition-friendly indexes
CREATE INDEX idx_kb_chunks_org ON kb_chunks(org_id);
CREATE INDEX idx_kb_chunks_kb ON kb_chunks(knowledge_base_id);
CREATE INDEX idx_kb_documents_kb ON kb_documents(knowledge_base_id);
CREATE INDEX idx_knowledge_bases_org ON knowledge_bases(org_id);
```

**Why pgvector over Pinecone/Weaviate:** Zero new infrastructure. Runs in our existing Railway Postgres. Handles millions of chunks per org. When a customer needs more, we can migrate their partition to a dedicated vector DB — but for 95% of use cases, pgvector is plenty.

---

### Onboarding Flow — Seamless Integration

The knowledge base setup is woven into the EXISTING onboarding wizard, not a separate flow. The goal: **a customer can go from zero to "AI that knows my company" in under 10 minutes.**

#### Updated Onboarding Wizard (7 steps, was 5)

```
Step 1: Welcome                          (existing)
Step 2: Select Providers                 (existing)
Step 3: Select IaC Tool                  (existing)
Step 4: ★ Knowledge Base Setup (NEW)     ← inserted here
Step 5: Generated Code (updated w/ KB permissions)
Step 6: Validate Credentials             (existing)
Step 7: Success                          (existing)
```

#### Step 4: Knowledge Base Setup (NEW)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  📚 Knowledge Base (Optional)                                   │
│                                                                 │
│  Give your AI access to company knowledge — HR docs,            │
│  product guides, support articles, anything your team           │
│  needs to reference.                                            │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ ☐ Enable         │  │ ☐ Skip for now   │                     │
│  │   Knowledge Base │  │   (can add later) │                     │
│  └──────────────────┘  └──────────────────┘                     │
│                                                                 │
│  ─── If enabled: ───────────────────────────────────────────    │
│                                                                 │
│  Where are your documents stored?                               │
│                                                                 │
│  ┌────────────┐  ┌────────────────┐  ┌────────────┐            │
│  │  ☁️ AWS    │  │  🔷 Azure      │  │  🔺 GCP    │            │
│  │  S3 Bucket │  │  Blob Storage  │  │  GCS Bucket│            │
│  └────────────┘  └────────────────┘  └────────────┘            │
│                                                                 │
│  ┌────────────────────────────────────────────┐                 │
│  │  📤 Direct Upload                          │                 │
│  │  Upload files through Bonito (up to 50MB)  │                 │
│  └────────────────────────────────────────────┘                 │
│                                                                 │
│  ─── If S3 selected: ──────────────────────────────────────     │
│                                                                 │
│  Bucket name:    [ my-company-docs          ]                   │
│  Prefix (opt):   [ hr-policies/             ]                   │
│  Region:         [ us-east-1            ▼   ]                   │
│                                                                 │
│  ─── Sync schedule: ───────────────────────────────────────     │
│                                                                 │
│  ○ Manual (sync when I want)                                    │
│  ○ Daily (midnight UTC)                                         │
│  ○ Weekly (Sunday midnight UTC)                                 │
│  ○ On file change (webhook — requires S3 event notification)    │
│                                                                 │
│                          [ Continue → ]                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**UX principle:** One screen, minimal inputs. Pick your storage, give us the bucket name, done. The IaC template handles all the permissions automatically.

#### Step 5: Generated IaC (Updated with KB Permissions)

When the user enables Knowledge Base, the generated Terraform/Pulumi/CloudFormation code **automatically includes** the read permissions for their selected storage:

---

### IaC Template Changes — Dynamic Permission Generation

The existing IaC engine (`backend/app/services/iac_templates.py`) already generates provider-specific code. We add a `knowledge_base` option that injects additional permissions.

#### AWS — S3 Read Permissions (added when KB enabled)

**Terraform:**
```hcl
# ── Knowledge Base: S3 Read Access ──────────────────────────
# Allows Bonito to read documents from your S3 bucket for
# AI knowledge base indexing. Read-only — no write/delete.

resource "aws_iam_policy" "bonito_kb_s3_read" {
  count = var.enable_knowledge_base ? 1 : 0
  name  = "bonito-kb-s3-read"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BonitoKBListBucket"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = "arn:aws:s3:::${var.kb_s3_bucket}"
      },
      {
        Sid    = "BonitoKBReadObjects"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = "arn:aws:s3:::${var.kb_s3_bucket}/${var.kb_s3_prefix}*"
      }
    ]
  })
}

resource "aws_iam_user_policy_attachment" "bonito_kb" {
  count      = var.enable_knowledge_base ? 1 : 0
  user       = aws_iam_user.bonito.name
  policy_arn = aws_iam_policy.bonito_kb_s3_read[0].arn
}

# Variables added for Knowledge Base
variable "enable_knowledge_base" {
  description = "Enable Bonito Knowledge Base (S3 read access)"
  type        = bool
  default     = false
}

variable "kb_s3_bucket" {
  description = "S3 bucket containing documents for Knowledge Base"
  type        = string
  default     = ""
}

variable "kb_s3_prefix" {
  description = "S3 prefix (folder) to scope document access"
  type        = string
  default     = ""
}
```

**CloudFormation:**
```yaml
# Knowledge Base S3 Read Policy (conditional)
BonitoKBS3ReadPolicy:
  Type: AWS::IAM::Policy
  Condition: EnableKnowledgeBase
  Properties:
    PolicyName: bonito-kb-s3-read
    Users:
      - !Ref BonitoUser
    PolicyDocument:
      Version: "2012-10-17"
      Statement:
        - Sid: BonitoKBReadObjects
          Effect: Allow
          Action:
            - s3:GetObject
            - s3:GetObjectVersion
            - s3:ListBucket
          Resource:
            - !Sub "arn:aws:s3:::${KBS3Bucket}"
            - !Sub "arn:aws:s3:::${KBS3Bucket}/${KBS3Prefix}*"

Parameters:
  EnableKnowledgeBase:
    Type: String
    Default: "false"
    AllowedValues: ["true", "false"]
  KBS3Bucket:
    Type: String
    Default: ""
  KBS3Prefix:
    Type: String
    Default: ""

Conditions:
  EnableKnowledgeBase: !Equals [!Ref EnableKnowledgeBase, "true"]
```

#### Azure — Blob Storage Read Permissions

**Terraform:**
```hcl
# ── Knowledge Base: Azure Blob Read Access ──────────────────
resource "azurerm_role_assignment" "bonito_kb_blob_reader" {
  count                = var.enable_knowledge_base ? 1 : 0
  scope                = "/subscriptions/${var.subscription_id}/resourceGroups/${var.resource_group}/providers/Microsoft.Storage/storageAccounts/${var.kb_storage_account}"
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azuread_service_principal.bonito.object_id
}

variable "enable_knowledge_base" {
  description = "Enable Bonito Knowledge Base (Blob Storage read access)"
  type        = bool
  default     = false
}

variable "kb_storage_account" {
  description = "Azure Storage Account containing documents"
  type        = string
  default     = ""
}

variable "kb_container_name" {
  description = "Blob container name for Knowledge Base documents"
  type        = string
  default     = ""
}
```

**Bicep:**
```bicep
@description('Enable Bonito Knowledge Base')
param enableKnowledgeBase bool = false

@description('Storage account for Knowledge Base documents')
param kbStorageAccount string = ''

// Blob Reader role for Knowledge Base
resource kbBlobReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableKnowledgeBase) {
  name: guid(subscription().id, bonitoSP.id, 'Storage Blob Data Reader')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1')
    principalId: bonitoSP.id
    principalType: 'ServicePrincipal'
  }
}
```

#### GCP — GCS Read Permissions

**Terraform:**
```hcl
# ── Knowledge Base: GCS Read Access ─────────────────────────
resource "google_storage_bucket_iam_member" "bonito_kb_viewer" {
  count  = var.enable_knowledge_base ? 1 : 0
  bucket = var.kb_gcs_bucket
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.bonito.email}"
}

variable "enable_knowledge_base" {
  description = "Enable Bonito Knowledge Base (GCS read access)"
  type        = bool
  default     = false
}

variable "kb_gcs_bucket" {
  description = "GCS bucket containing documents for Knowledge Base"
  type        = string
  default     = ""
}

variable "kb_gcs_prefix" {
  description = "GCS prefix to scope document access"
  type        = string
  default     = ""
}
```

**Key security principle:** All IaC templates grant **read-only** access to the specific bucket/container the customer specifies. No write. No delete. No access to other buckets. Prefix-scoped where possible.

---

### API Design

#### Knowledge Base Management

```
# CRUD for knowledge bases
POST   /api/knowledge-bases                    Create a new knowledge base
GET    /api/knowledge-bases                    List all KBs for the org
GET    /api/knowledge-bases/{kb_id}            Get KB details + stats
PUT    /api/knowledge-bases/{kb_id}            Update KB config
DELETE /api/knowledge-bases/{kb_id}            Delete KB and all chunks

# Document management
POST   /api/knowledge-bases/{kb_id}/documents          Upload file(s) directly
POST   /api/knowledge-bases/{kb_id}/sync               Trigger sync from cloud storage
GET    /api/knowledge-bases/{kb_id}/documents           List documents
GET    /api/knowledge-bases/{kb_id}/documents/{doc_id}  Document details + chunks
DELETE /api/knowledge-bases/{kb_id}/documents/{doc_id}  Remove document

# Search / test
POST   /api/knowledge-bases/{kb_id}/search     Search KB (test retrieval)
        Body: {"query": "...", "top_k": 5}
        Returns: matching chunks with scores + source info

# Sync status
GET    /api/knowledge-bases/{kb_id}/sync-status   Current sync progress
```

#### Gateway Integration — Zero Code Change for Customers

The beauty: customers using the OpenAI-compatible gateway just add ONE field:

```python
# Standard call (no knowledge base):
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What's our PTO policy?"}]
)

# Knowledge-augmented call (just add extra_body):
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What's our PTO policy?"}],
    extra_body={"bonito": {"knowledge_base": "hr-docs"}}
)

# Or via custom header (for non-Python clients):
# X-Bonito-Knowledge-Base: hr-docs
```

**Alternative: routing policy attachment.** Attach a knowledge base to a routing policy so ALL requests through that policy get knowledge augmentation automatically. Zero code changes:

```python
# In dashboard: attach "hr-docs" KB to policy "support-chat"
# Now every request using the rt-xxx key for that policy
# automatically gets RAG — no extra_body needed
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "What's our PTO policy?"}],
    # That's it. KB is attached at the policy level.
)
```

---

### Gateway RAG Middleware

The retrieval logic sits as middleware in the gateway pipeline, between authentication and model routing:

```
Request → Auth → Rate Limit → [RAG Middleware] → Route → Provider → Response
                                    │
                              1. Detect KB (from request body, header, or policy)
                              2. Embed query (cheapest embedding model)
                              3. Vector search (pgvector, top_k=5)
                              4. Build augmented prompt:
                                 │
                                 │  System: "Use the following context to answer.
                                 │           Cite sources when possible.
                                 │           If the context doesn't contain the
                                 │           answer, say so."
                                 │
                                 │  Context:
                                 │    [1] {chunk.content} (source: benefits.pdf, p.3)
                                 │    [2] {chunk.content} (source: pto-policy.md)
                                 │    ...
                                 │
                                 │  User: {original query}
                                 │
                              5. Forward augmented prompt to model
                              6. Add source citations to response metadata
```

**Response format** (extends OpenAI format):
```json
{
  "id": "chatcmpl-xxx",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "According to our PTO policy, full-time employees receive 20 days..."
    }
  }],
  "usage": {
    "prompt_tokens": 850,
    "completion_tokens": 120,
    "total_tokens": 970
  },
  "bonito": {
    "knowledge_base": "hr-docs",
    "sources": [
      {
        "document": "pto-policy.pdf",
        "page": 3,
        "section": "Annual Leave Entitlement",
        "relevance_score": 0.94,
        "chunk_preview": "Full-time employees are entitled to 20 days..."
      },
      {
        "document": "employee-handbook.md",
        "section": "Benefits Overview",
        "relevance_score": 0.87,
        "chunk_preview": "PTO accrues at 1.67 days per month..."
      }
    ],
    "retrieval_cost": 0.00002,
    "retrieval_latency_ms": 45
  }
}
```

---

### Dashboard Pages

#### 1. Knowledge Bases Page (`/knowledge-bases`)

```
┌─────────────────────────────────────────────────────────────────┐
│  📚 Knowledge Bases                         [ + New Knowledge Base ]│
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  📁 hr-docs                                    ● Ready   │   │
│  │  Source: S3 → my-company-docs/hr-policies/               │   │
│  │  47 documents · 2,340 chunks · Last synced 2h ago        │   │
│  │  Embedding: amazon.titan-embed-text-v2                   │   │
│  │  [View Docs]  [Search]  [Sync Now]  [Settings]           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  📁 product-docs                               ● Syncing │   │
│  │  Source: GCS → product-documentation/                     │   │
│  │  124 documents · 8,901 chunks · Syncing... 67%           │   │
│  │  Embedding: text-embedding-005                           │   │
│  │  [View Docs]  [Search]  [Settings]                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  📁 support-articles                           ● Ready   │   │
│  │  Source: Direct Upload                                    │   │
│  │  23 documents · 456 chunks · Last synced 5d ago          │   │
│  │  Embedding: text-embedding-3-small                       │   │
│  │  [View Docs]  [Search]  [Upload]  [Settings]             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 2. Knowledge Base Detail Page (`/knowledge-bases/{id}`)

- Document list with status (processed, pending, error)
- Search/test panel: type a query, see which chunks come back with relevance scores
- Usage analytics: how many queries hit this KB, which documents are most referenced
- Sync history: when it last synced, how many docs changed, any errors
- Settings: chunk size, overlap, embedding model, sync schedule, attached policies

#### 3. Integration into Existing Pages

- **Routing Policies page**: New "Knowledge Base" dropdown when creating/editing a policy. Attach a KB to a policy = automatic RAG for all requests through that policy.
- **Gateway Logs**: New column "KB" showing which knowledge base (if any) was used for each request
- **Analytics**: Knowledge base usage stats — queries per KB, avg retrieval latency, top-referenced documents
- **Playground**: Toggle "Use Knowledge Base" when testing models — see how responses change with/without context

---

### CLI Commands

```bash
# Knowledge base management
bonito kb list                                    # List all knowledge bases
bonito kb create --name "hr-docs" --source s3 \
  --bucket my-docs --prefix hr/                   # Create from S3
bonito kb create --name "uploads" --source upload  # Create for direct upload
bonito kb info <kb-id>                            # Details + stats
bonito kb delete <kb-id>                          # Delete KB

# Document management
bonito kb docs <kb-id>                            # List documents in KB
bonito kb upload <kb-id> ./file.pdf               # Upload a file
bonito kb upload <kb-id> ./docs/                  # Upload a directory
bonito kb sync <kb-id>                            # Trigger sync from storage

# Search / test
bonito kb search <kb-id> "What is our PTO policy?"  # Test retrieval
bonito kb search <kb-id> "..." --top-k 10            # More results

# Chat with knowledge
bonito chat -m gpt-4o --kb hr-docs "What's our PTO policy?"
```

---

### Pricing Integration

| Tier | Knowledge Base Limits |
|------|----------------------|
| **Free** | 1 KB, 100 documents, 10K chunks, manual sync only |
| **Pro** ($499/mo) | 5 KBs, unlimited documents, 500K chunks, scheduled sync |
| **Enterprise** ($2-5K/mo) | Unlimited KBs, unlimited everything, webhook sync, custom embedding models |
| **Scale** ($50K+/yr) | + dedicated vector DB, hybrid search (vector + keyword), advanced chunking strategies |

**Cost to Bonito:** pgvector storage is essentially free within existing Postgres. The only variable cost is embedding generation, which uses the customer's own cloud credits via the gateway.

---

### Build Plan

| Week | Deliverable |
|------|------------|
| **1** | **Foundation**: pgvector extension + migrations, `knowledge_bases` / `kb_documents` / `kb_chunks` tables, CRUD API endpoints, document parsing pipeline (PDF/DOCX/TXT/MD/HTML), chunking engine |
| **2** | **Embeddings + Storage**: Embedding generation via gateway (route to cheapest embedding model), pgvector write/search, sync engine (S3/Blob/GCS read), background job for batch processing |
| **3** | **Gateway Integration**: RAG middleware in gateway pipeline, knowledge base detection (request body / header / policy attachment), prompt augmentation with context injection, source citations in response |
| **4** | **Frontend + Polish**: Knowledge Bases dashboard page, KB detail page with search/test, onboarding wizard Step 4, routing policy KB attachment, IaC template updates, CLI `kb` commands |
| **5** | **Testing + Launch**: E2E testing across all 3 clouds, performance testing (retrieval latency <100ms), sync reliability testing, documentation, deploy to prod |

---

### Cross-Cloud RAG — The Differentiator

This is what makes Bonito unique. Example scenario:

1. Company stores HR docs in **S3** (AWS account)
2. Product docs in **Azure Blob Storage** (Azure account)  
3. Support articles in **GCS** (GCP account)
4. All three get ingested into Bonito knowledge bases
5. A single query can search across ALL knowledge bases
6. The answer gets routed to **any model on any cloud** via smart routing

**No cloud provider can do this.** AWS KB → Bedrock only. Azure AI Search → Azure only. GCP RAG → Vertex only. Bonito breaks the wall.

---

## Near-Term (Next 2-4 weeks)

### ⚡ Gateway Scaling (Done + Next)
- [x] Workers 2→4 (start-prod.sh default)
- [x] Redis connection pool (20 max connections, configurable)
- [x] `ADMIN_EMAILS` env var for platform admin access
- [x] Platform admin portal (org/user management, system stats, knowledge base)
- [ ] Railway replicas (2-3 instances) — when first paying customer arrives
- [ ] Move router cache + Azure AD tokens to Redis (shared across workers/instances)
- [ ] Vault credential caching in Redis (reduce Vault calls on router rebuild)
- [ ] Per-tier rate limits (Free: 30/min, Pro: 300/min, Enterprise: custom)

### 🔧 Production Polish
- [ ] Fix Azure deployment gap — zero deployments despite 133 models; need API key auth or TPM quota allocation
- [ ] Analytics endpoint — `/api/gateway/analytics` returns 404, needs fix or redirect to `/api/gateway/logs`
- [ ] Gateway logs field consistency — some fields show blank in list view
- [ ] UI warning when provider has 0 active deployments

### 🔐 SSO / SAML
- [ ] SAML 2.0 integration for enterprise SSO
- [ ] Support Okta, Azure AD, Google Workspace
- [ ] Role mapping from IdP groups → Bonito roles (admin, member, viewer)
- [ ] Session management & token refresh for SSO users

### 🖥️ CLI Finalization
- [x] Core commands: auth, providers, models, deployments, chat, gateway, policies, analytics
- [x] All CLI field mappings tested + fixed against prod (9 bugs, commit 75f7a86)
- [x] Publish to PyPI as `bonito-cli` (v0.5.1 live)
- [ ] `bonito doctor` command — diagnose connectivity, auth, provider health
- [ ] Shell completions (bash/zsh/fish) via `bonito completion install`
- [ ] `--quiet` flag for CI/CD automation
- [ ] Homebrew formula / tap for macOS users
- [ ] README + docs page for CLI

---

## Medium-Term (1-3 months)

### 🧠 Smart Routing (Pro Feature) ⭐
_Complexity-aware model routing — auto-detect prompt complexity and route to the cheapest model that can handle it._

**Why:** Save 40-70% on AI spend without manual model selection. No competitor (LiteLLM, Portkey, Helicone) has this natively.

**Approach:** Classifier-based (Phase 1), then upgrade to embeddings (Phase 2).

**Phase 1 — Rule-Based Classifier (~1 week)**
- Heuristic scoring: token count, keyword detection (translate/summarize = simple; analyze/compare/code = complex)
- Map complexity tiers to model tiers (e.g., simple → Flash Lite, medium → Flash, complex → Pro)
- Configurable thresholds per routing policy
- New strategy type: `smart_routing` alongside existing cost_optimized, failover, etc.

**Phase 2 — Embedding-Based (~2-3 weeks)**
- Embed prompts, cluster into complexity buckets using historical data
- Train on org's own usage patterns (personalized routing)
- A/B test against rule-based to measure savings

**Packaging:**
- Free tier: rule-based routing only (failover, cost-optimized, A/B test)
- **Pro ($499/mo): Smart routing ON** — the headline feature
- Enterprise: smart routing + custom model tiers + SLA + routing analytics dashboard showing savings

**Competitive positioning:** "Connect your clouds, turn on smart routing, save 50%+ on AI spend."

### 🏗️ VPC Gateway — Bonito Agent (Enterprise) ⭐
_Data-sovereign AI gateway deployed into customer's VPC. Control plane stays SaaS._

---

#### Core Principle: Unified API Contract

**The frontend, dashboard, and all management APIs are identical regardless of deployment mode.** Whether data comes from our shared gateway or a customer's VPC agent, it lands in the same Postgres tables via the same schema. The frontend never knows the difference.

```
Mode A — Shared Gateway (Free/Pro):
  Customer App → Bonito Gateway (Railway) → logs directly to Postgres
                                                    ↑
                                            Dashboard reads same tables

Mode B — VPC Agent (Enterprise):
  Customer App → Bonito Agent (VPC) → pushes metadata → /api/agent/ingest → same Postgres tables
                                                                                    ↑
                                                                            Dashboard reads same tables
```

Same `GatewayRequest` rows. Same `/api/gateway/usage` endpoint. Same costs page. Same analytics. Same alerts. **Zero frontend changes.**

---

#### Architecture: Control Plane / Data Plane Split

```
┌─── Customer VPC ─────────────────────────────────────────────────┐
│                                                                   │
│  ┌─────────────┐     ┌──────────────────────────────────────┐    │
│  │ Customer App │────→│ Bonito Agent                         │    │
│  │ (their code) │     │                                      │    │
│  └─────────────┘     │  ┌─────────────┐  ┌───────────────┐  │    │
│                       │  │ LiteLLM     │  │ Config Sync   │  │    │
│  ┌─────────────┐     │  │ Proxy       │  │ Daemon        │  │    │
│  │ Customer App │────→│  │ - routing   │  │ - pulls every │  │    │
│  │ (their code) │     │  │ - failover  │  │   30s         │  │    │
│  └─────────────┘     │  │ - rate limit │  │ - hot-reload  │  │    │
│                       │  └──────┬──────┘  └───────┬───────┘  │    │
│                       │         │                  │          │    │
│                       │  ┌──────┴──────┐  ┌───────┴───────┐  │    │
│                       │  │ Metrics     │  │ Health        │  │    │
│                       │  │ Reporter    │  │ Reporter      │  │    │
│                       │  │ - batches   │  │ - heartbeat   │  │    │
│                       │  │   every 10s │  │   every 60s   │  │    │
│                       │  └──────┬──────┘  └───────┬───────┘  │    │
│                       └─────────┼─────────────────┼──────────┘    │
│                                 │                 │               │
│     ┌───────────────────┐       │                 │               │
│     │ Customer's Cloud  │       │                 │               │
│     │ ├── AWS Bedrock   │◄──────┤ DATA PLANE      │               │
│     │ ├── Azure OpenAI  │  (stays in VPC)         │               │
│     │ └── GCP Vertex AI │       │                 │               │
│     └───────────────────┘       │                 │               │
│                                 │                 │               │
│     ┌───────────────────┐       │                 │               │
│     │ Customer Secrets  │       │                 │               │
│     │ Manager           │◄──────┘                 │               │
│     │ (AWS SM / AZ KV / │  credentials            │               │
│     │  GCP SM)          │  stay local              │               │
│     └───────────────────┘                         │               │
└─────────────────────────────────┼─────────────────┼───────────────┘
                                  │                 │
                          outbound HTTPS only (443)
                                  │                 │
┌─────────────────────────────────┼─────────────────┼───────────────┐
│              Bonito Control Plane (Railway)        │               │
│                                 │                 │               │
│  ┌──────────────────────────────┴─────────────────┴────────────┐  │
│  │ Agent Ingestion API                                          │  │
│  │                                                              │  │
│  │  POST /api/agent/ingest     ← metrics (token counts, cost,  │  │
│  │                                latency, model, status)       │  │
│  │  GET  /api/agent/config     → policies, keys, routing rules  │  │
│  │  POST /api/agent/heartbeat  ← agent health, version, uptime │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                 │                                  │
│  ┌──────────────────────────────┴──────────────────────────────┐  │
│  │ Postgres (same tables, same schema)                          │  │
│  │                                                              │  │
│  │  gateway_requests  ← identical rows from shared GW or agent  │  │
│  │  gateway_keys      ← synced to agent for local auth          │  │
│  │  policies          ← synced to agent for local enforcement   │  │
│  │  routing_policies  ← synced to agent for local routing       │  │
│  │  gateway_configs   ← synced to agent for provider settings   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                 ↑                                  │
│  ┌──────────────────────────────┴──────────────────────────────┐  │
│  │ Existing Dashboard APIs (unchanged)                          │  │
│  │                                                              │  │
│  │  GET /api/gateway/usage     → reads gateway_requests table   │  │
│  │  GET /api/gateway/logs      → reads gateway_requests table   │  │
│  │  GET /api/gateway/keys      → reads gateway_keys table       │  │
│  │  PUT /api/gateway/config    → writes config, syncs to agent  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                 ↑                                  │
└─────────────────────────────────┼──────────────────────────────────┘
                                  │
┌─────────────────────────────────┼──────────────────────────────────┐
│              getbonito.com (Vercel) — NO CHANGES                   │
│                                 │                                  │
│  Dashboard, Analytics, Costs, Governance, Team, Alerts             │
│  All pages read from the same APIs, same tables                    │
│  Frontend has ZERO awareness of shared vs VPC mode                 │
└────────────────────────────────────────────────────────────────────┘
```

---

#### What Stays in VPC (Data Plane)

| Data | Where it lives | Never leaves VPC |
|------|---------------|-----------------|
| Prompts & responses | Customer app ↔ Agent ↔ Cloud provider | ✅ |
| Cloud credentials | Customer's secrets manager | ✅ |
| Request/response payloads | In-memory during processing | ✅ |
| Model inference | Customer's cloud account | ✅ |

#### What Syncs to Control Plane

| Data | Direction | Frequency | Format |
|------|-----------|-----------|--------|
| Usage metrics | Agent → Railway | Every 10s (batched) | `GatewayRequest` schema (no content) |
| Agent health | Agent → Railway | Every 60s | Heartbeat: uptime, version, connected providers |
| Policies | Railway → Agent | Agent pulls every 30s | Model allow-lists, spend caps, rate limits |
| API key registry | Railway → Agent | Agent pulls every 30s | Key hashes for local authentication |
| Routing policies | Railway → Agent | Agent pulls every 30s | Failover chains, A/B weights, strategies |
| Gateway config | Railway → Agent | Agent pulls every 30s | Enabled providers, default settings |

**Metrics payload per request** (identical to shared gateway's `GatewayRequest` row):
```json
{
  "model_requested": "gpt-4o",
  "model_used": "gpt-4o",
  "input_tokens": 500,
  "output_tokens": 200,
  "cost": 0.0035,
  "latency_ms": 1200,
  "status": "success",
  "key_id": "uuid",
  "provider": "azure",
  "timestamp": "2026-02-17T11:20:00Z"
}
```
No prompts. No responses. Just the numbers our dashboard already expects.

---

#### How Every Dashboard Feature Works with VPC Agent

| Feature | Shared Gateway (today) | VPC Agent (enterprise) | Frontend change? |
|---------|----------------------|----------------------|-----------------|
| **Costs page** | Reads `gateway_requests` directly | Same — agent pushes to same table | None |
| **Analytics** | Reads `gateway_requests` directly | Same — agent pushes to same table | None |
| **Gateway logs** | Reads `gateway_requests` directly | Same — agent pushes to same table | None |
| **Alerts / spend caps** | Control plane checks DB | Same — data came from agent push | None |
| **Policies** | Enforced in gateway process | Synced to agent, enforced locally | None |
| **Routing policies** | Applied in gateway process | Synced to agent, applied locally | None |
| **API key management** | Keys validated in gateway | Key hashes synced to agent for local validation | None |
| **Team management** | Control plane only | Control plane only | None |
| **Model catalog** | Synced from cloud APIs | Agent reports available models | None |
| **Playground** | Routes through our gateway | ⚠️ Routes through our infra (with note) | Minor UX note |
| **Audit logs** | Logged in gateway | Agent pushes audit events | None |
| **Governance** | Enforced in gateway | Synced + enforced locally by agent | None |

---

#### Bonito Agent — Technical Specification

**Container image**: `ghcr.io/bonito/gateway-agent:latest` (~50-100MB)

```
bonito-gateway-agent
├── LiteLLM Proxy (data plane)
│   ├── OpenAI-compatible API (/v1/chat/completions, /v1/embeddings, etc.)
│   ├── Model routing: failover, cost-optimized, A/B test, round-robin
│   ├── Rate limiting (in-memory or local Redis)
│   ├── Policy enforcement (cached from control plane)
│   └── Credential loading (from customer's secrets manager)
│
├── Config Sync Daemon (control plane client)
│   ├── GET /api/agent/config — pulls every 30s
│   │   ├── Active policies (model access, spend caps)
│   │   ├── API key hashes (for local authentication)
│   │   ├── Routing policies (strategies, model priorities)
│   │   └── Gateway config (enabled providers, defaults)
│   ├── Diffing — only applies changes, no full reload
│   ├── Local cache — works offline with last-known config
│   └── Hot-reload — zero-downtime config updates
│
├── Metrics Reporter (telemetry)
│   ├── POST /api/agent/ingest — batches every 10s
│   ├── Writes to same GatewayRequest schema
│   ├── Retry queue — buffers if control plane unreachable
│   └── Compression — gzip payloads for bandwidth efficiency
│
└── Health Reporter
    ├── POST /api/agent/heartbeat — every 60s
    ├── Reports: uptime, version, request count, error rate
    ├── Connected providers and their health
    └── Control plane alerts admin if heartbeat missed >5 min
```

**NOT included in agent** (stays on control plane):
- PostgreSQL database
- HashiCorp Vault
- Frontend / dashboard
- User authentication (JWT, sessions)
- Email service (Resend)
- Notification system

---

#### Authentication Model

Three token types, clear separation of concerns:

| Token | Prefix | Who uses it | Purpose |
|-------|--------|------------|---------|
| **User API key** | `bn-` | Customer's apps → Agent | Authenticate AI requests |
| **Routing policy key** | `rt-` | Customer's apps → Agent | Route via specific policy |
| **Org token** | `bt-` | Agent → Control plane | Config sync, metrics push, heartbeat |

**Org token provisioning flow:**
1. Enterprise customer enables "VPC Mode" in dashboard settings
2. Control plane generates `bt-xxxxx` org token
3. Admin copies token into their agent deployment config
4. Agent uses token for all control plane communication
5. Token can be rotated from dashboard without redeploying agent

**Customer app migration** — SDK-compatible, just change base URL:
```python
# Before (shared gateway):
client = OpenAI(base_url="https://api.getbonito.com/v1", api_key="bn-xxx")

# After (VPC agent) — same key, same API, just a URL change:
client = OpenAI(base_url="http://bonito-agent.internal:8000/v1", api_key="bn-xxx")
```

---

#### Backend Changes Required

**New API endpoints** (added to Railway backend):

```python
# Agent-facing endpoints (authenticated via bt- org token)
POST /api/agent/ingest          # Receive batched metrics from agent
GET  /api/agent/config          # Serve current config snapshot for agent
POST /api/agent/heartbeat       # Receive agent health status
GET  /api/agent/keys            # Serve API key hashes for local validation

# Dashboard endpoints (new)
GET  /api/admin/agents          # List all VPC agents across orgs
GET  /api/orgs/{id}/agent       # Agent status for specific org
POST /api/orgs/{id}/agent/token # Generate/rotate org token
```

**Agent ingestion service** (`app/services/agent_ingest.py`):
```python
async def ingest_metrics(org_id: UUID, batch: list[dict], db: AsyncSession):
    """Write agent-pushed metrics into the same GatewayRequest table.
    
    Identical schema to what the shared gateway writes directly.
    The dashboard/analytics/costs pages read from this table
    regardless of source.
    """
    for record in batch:
        entry = GatewayRequest(
            org_id=org_id,
            key_id=record.get("key_id"),
            model_requested=record["model_requested"],
            model_used=record["model_used"],
            input_tokens=record["input_tokens"],
            output_tokens=record["output_tokens"],
            cost=record["cost"],
            latency_ms=record["latency_ms"],
            status=record["status"],
            provider=record.get("provider"),
            source="vpc_agent",  # new column to distinguish origin
        )
        db.add(entry)
```

**New DB column** (one migration):
```sql
ALTER TABLE gateway_requests ADD COLUMN source VARCHAR(20) DEFAULT 'shared_gateway';
-- Values: 'shared_gateway' | 'vpc_agent'
-- Used for admin visibility only; dashboard queries don't filter on it
```

---

#### Agent Container — Deployment Options

**Option A: Docker Compose** (small teams, single VM)
```yaml
version: "3.8"
services:
  bonito-agent:
    image: ghcr.io/bonito/gateway-agent:latest
    environment:
      BONITO_CONTROL_PLANE: https://api.getbonito.com
      BONITO_ORG_TOKEN: bt-xxxxx
      # Credential source (pick one per provider)
      AWS_SECRETS_MANAGER_ARN: arn:aws:secretsmanager:us-east-1:123:secret:bonito-aws
      AZURE_KEY_VAULT_URL: https://myvault.vault.azure.net
      GCP_SECRET_NAME: projects/123/secrets/bonito-gcp
    ports:
      - "8000:8000"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

**Option B: Kubernetes / Helm** (production, HA)
```bash
helm repo add bonito https://charts.getbonito.com
helm install bonito-gateway bonito/gateway-agent \
  --set controlPlane.url=https://api.getbonito.com \
  --set controlPlane.token=bt-xxxxx \
  --set replicas=3 \
  --set resources.requests.memory=256Mi \
  --set resources.limits.memory=512Mi \
  --set credentials.aws.secretsManagerArn=arn:aws:secretsmanager:... \
  --namespace bonito
```

**Option C: Terraform** (IaC, full automation)

AWS ECS/Fargate:
```hcl
module "bonito_gateway" {
  source              = "bonito/gateway-agent/aws"
  version             = "~> 1.0"
  vpc_id              = var.vpc_id
  subnet_ids          = var.private_subnet_ids
  org_token           = var.bonito_org_token
  desired_count       = 2
  cpu                 = 512
  memory              = 1024
  secrets_manager_arn = var.credentials_secret_arn
  
  tags = {
    Environment = "production"
    ManagedBy   = "bonito"
  }
}

output "agent_endpoint" {
  value = module.bonito_gateway.internal_url
  # e.g., http://bonito-agent.internal:8000
}
```

Azure Container Apps:
```hcl
module "bonito_gateway" {
  source            = "bonito/gateway-agent/azure"
  version           = "~> 1.0"
  resource_group    = var.resource_group_name
  vnet_id           = var.vnet_id
  subnet_id         = var.container_apps_subnet_id
  org_token         = var.bonito_org_token
  key_vault_url     = var.key_vault_url
  min_replicas      = 2
  max_replicas      = 5
}
```

GCP Cloud Run:
```hcl
module "bonito_gateway" {
  source         = "bonito/gateway-agent/gcp"
  version        = "~> 1.0"
  project_id     = var.project_id
  region         = "us-central1"
  vpc_connector  = var.vpc_connector_name
  org_token      = var.bonito_org_token
  secret_name    = var.gcp_secret_name
  min_instances  = 2
  max_instances  = 10
}
```

---

#### Dashboard Integration

**New UI elements** (added to existing dashboard, not a separate app):

1. **Settings → Deployment Mode toggle**
   - "Shared Gateway" (default) vs "VPC Agent"
   - Enabling VPC mode generates the `bt-` org token
   - Shows deployment instructions (Docker/Helm/Terraform snippets)

2. **Agent Status indicator** (header bar when VPC mode is on)
   - 🟢 Agent connected (last heartbeat <2 min ago)
   - 🟡 Agent delayed (last heartbeat 2-5 min ago)
   - 🔴 Agent offline (last heartbeat >5 min ago, alert sent)

3. **Admin → Agents page** (platform admin only)
   - List all VPC agents across all orgs
   - Health status, version, uptime, request rate
   - Per-agent config sync status

4. **Analytics page** — no changes needed
   - Optional: add "Source" filter (Shared Gateway / VPC Agent) for admin visibility
   - Data is identical in either case

---

#### Graceful Degradation

| Failure | Agent behavior | Control plane behavior |
|---------|---------------|----------------------|
| Control plane unreachable | Continue serving with last-known config. Queue metrics for retry (up to 1 hour buffer). | Show agent as "delayed" then "offline". Alert admin. |
| Customer's cloud provider down | LiteLLM failover to next provider (if configured). Return 502 if all providers fail. | Show elevated error rate in analytics. |
| Agent crash / OOM | Container orchestrator restarts automatically. Metrics gap during downtime. | Show gap in analytics timeline. Alert admin. |
| Credentials expired | Agent detects 401 from cloud provider. Attempts to re-read from secrets manager. Logs error if refresh fails. | Error rate spike visible in dashboard. |
| Config sync conflict | Agent always takes latest from control plane (last-write-wins). | N/A — control plane is source of truth. |

---

#### Security Considerations

- **Outbound only**: Agent initiates all connections. No inbound ports required from internet.
- **mTLS optional**: Agent ↔ control plane can use mutual TLS for additional assurance.
- **Org token rotation**: Rotatable from dashboard without redeploying agent (agent picks up new token on next sync).
- **No data exfiltration**: Agent code is open for customer audit. Only metadata (counts, costs) leaves VPC.
- **Network policies**: Agent only needs outbound to: (1) Bonito control plane, (2) Cloud AI endpoints. Everything else blocked.
- **Container signing**: Agent images signed with cosign for supply chain integrity.

---

#### Build Timeline — Detailed

| Week | Deliverable | Details |
|------|------------|---------|
| **1** | Gateway service split | Refactor `gateway.py` into shared `core` + `full_mode` (Railway) + `agent_mode` (VPC). Config sync protocol spec. Agent Dockerfile. |
| **2** | Agent container + ingestion API | Working agent image. `POST /api/agent/ingest`, `GET /api/agent/config`, `POST /api/agent/heartbeat`. Org token (`bt-`) auth. E2E test: agent → control plane → dashboard shows data. |
| **3** | Terraform modules + Helm chart | AWS ECS module, Azure Container Apps module, GCP Cloud Run module. Helm chart with values.yaml. CI/CD pipeline for agent image builds. |
| **4** | Dashboard integration + polish | Settings → VPC mode toggle. Agent status indicator. Admin agents page. Deployment instructions in-app. Documentation. Customer onboarding runbook. |

**Pricing:** Enterprise tier $2K-$5K/mo base + usage

### 📊 Advanced Analytics
- [ ] Cost optimization recommendations (auto-suggest cheaper models based on usage)
- [ ] Model performance comparison dashboard
- [ ] Department-level cost attribution
- [ ] Budget alerts and automatic throttling
- [ ] Weekly digest emails via Resend

### 🧠 Bonobot Conversational Memory (Persistent Recall)
_Agents that remember across sessions -- auto-extract facts from conversations, auto-inject relevant memories into context._

**Why:** KB retrieval (structured docs) scores 92%+ but conversational memory (recalling details from past chats) is weak. Enterprise customers need agents that learn from interactions over time -- support agents that remember past tickets, sales agents that recall deal context, onboarding agents that know what was already covered.

**Current state:** `AgentMemoryService` exists with full pgvector search, but is disconnected from the execute loop. Memory only works via explicit API calls. The `/execute` endpoint never searches or stores memories.

**Approach (safe, opt-in):**
- [ ] Feature flag per agent: `persistent_memory: true` in agent config. Off by default. Existing agents untouched.
- [ ] **Read path**: Before generating response, search `agent_memories` for relevant context. Inject top-K matches into system prompt alongside KB results.
- [ ] **Write path**: After each conversation turn, extract key facts (lightweight, not full LLM extraction every time). Store with embeddings.
- [ ] **Smarter chunking**: Chunk by topic/fact, not by session. A single conversation might produce 3-5 discrete memories.
- [ ] **Decay/consolidation**: Importance scoring with access-based boosting. Memories that keep getting retrieved stay strong; unused ones decay.
- [ ] **LOCOMO benchmark target**: 50%+ overall (from current 27%), 85%+ single-hop (from 74%).

**LOCOMO Benchmark (baseline, 2026-03-22):**
- Combined: 134/497 = 27.0% (3 samples, Llama 3.1 8B via Groq)
- Single-hop: 74.2% | Multi-hop: 18.5% | Temporal: 50% | Open-domain: 18.6% | Adversarial: 9.8%
- Note: String-matching eval is too strict. Semantic accuracy estimated ~35-45%.

**Build plan:** ~1 week. Wire read/write into execute loop behind flag, add fact extraction prompt, test against NovaMart (regression) + LOCOMO (improvement).

### 🤖 Agent Framework (Phase 19+)
- [ ] Agent registry -- define AI agents with tool chains
- [ ] Agent observability — trace multi-step agent runs
- [ ] Agent cost attribution — who/what is spending
- [ ] Multi-model agent pipelines (chain cheap→expensive for RAG patterns)

---

## Near-Term (Next Up)

### 💳 Stripe Integration
- [ ] Stripe Checkout for Pro tier ($499/mo)
- [ ] Webhook handler for subscription lifecycle (created, updated, cancelled)
- [ ] Automatic tier upgrade/downgrade on payment status change
- [ ] Usage-based billing metering (gateway calls, tokens)
- [ ] Customer portal for billing management
- [ ] Free → Pro upgrade flow in dashboard + CLI

### 🏗️ VPC Gateway (Enterprise)
- [ ] Self-hosted gateway binary deployed into customer's VPC
- [ ] Control plane stays hosted by Bonito (management, analytics, policies)
- [ ] Gateway ↔ control plane secure tunnel (mTLS)
- [ ] Customer data never leaves their network
- [ ] Kong/Istio-inspired architecture
- [ ] Terraform module for one-click VPC deployment

### 🔗 Agent-to-Agent Connections (Bonobot)
- [ ] E2E test invoke_agent delegation via CLI
- [ ] Connection creation/management in CLI (`bonito agents connect`)
- [ ] Visual connection editing in React Flow canvas
- [ ] Cross-project agent invocation (Enterprise only)
- [ ] **Embedded Agent Test Console** - in-UI terminal/chat panel to test agent networks live. Type a message, watch it route through the network in real time, see logs stream. Like Playground but for agent networks instead of single model calls.

### 🔧 Production Polish
- [ ] Vault client cache TTL (currently no expiry — stale reads possible)
- [ ] GCP model aliasing (friendly names for Vertex AI models)
- [ ] CLI `plan show` endpoint (subscription info via API)
- [x] CLI merge `feature/bonito-cli` branch → `main`
- [ ] Azure deployment auto-creation on provider connect (skip manual step)

## Long-Term (3-6 months)

### 🌐 Marketplace
- [ ] Pre-built routing templates (cost-saver, quality-first, compliance-focused)
- [ ] Community-shared policies and configurations
- [ ] Partner integrations (LangChain, LlamaIndex, CrewAI)

### 🔒 Compliance & Governance
- [ ] Full SOC2 / HIPAA compliance checks (not just structural)
- [ ] Data residency enforcement (route to specific regions only)
- [ ] PII detection and redaction in prompts
- [ ] Audit log export (SIEM integration)
- [ ] DLP policies — block certain content from leaving the org

### 📱 Multi-Channel
- [ ] Slack bot for team model management
- [ ] Teams integration for enterprise orgs
- [ ] Mobile app (iOS/Android) for monitoring

---

## Pricing Strategy
| Tier | Price | Key Features |
|------|-------|-------------|
| Free | $0 | 3 providers, basic routing, 1K requests/mo |
| Pro | $499/mo | **Smart routing**, unlimited requests, analytics, API keys |
| Enterprise | $2K-$5K/mo | VPC gateway, SSO/SAML, compliance, SLA |
| Scale | $50K-$100K+/yr | Dedicated support, custom integrations, volume pricing |

---

## Competitor Watch
| Competitor | Smart Routing? | Self-Hosted? | Notes |
|-----------|---------------|-------------|-------|
| LiteLLM | ❌ Rule-based only | ✅ | OSS proxy, no complexity awareness |
| Portkey | ❌ Loadbalance/fallback | ❌ SaaS only | Good observability |
| Helicone | ❌ No routing | ❌ SaaS only | Logging/analytics focused |
| OpenRouter | ✅ via NotDiamond | ❌ Consumer | Not enterprise, adds dependency |
| CGAI | ❌ | ❌ | Crypto verification angle |
| Cloudflare AI GW | ❌ Basic | ❌ | Tied to CF ecosystem |

**Bonito's edge:** Integrated product (onboarding + IaC + console + governance + gateway + smart routing + agent) — not just a proxy.
