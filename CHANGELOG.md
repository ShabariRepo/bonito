# Changelog

All notable changes to Bonito will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.5.0] - 2026-04-07

### Added - Shared Conversational Memory (Memwright)
- **Memwright Integration** — Persistent per-session conversational memory for Bonobot agents
  - Automatic recall before inference (injected into system prompt as `## Conversation Memory`)
  - Automatic store after each response (user question + assistant reply)
  - Resolves referential follow-ups: "the third one", "from the list above", "those campaigns"
  - Per-session isolation: memories scoped to `{org_id}/{agent_id}/{session_id}`
  - Storage: SQLite + ChromaDB (standalone, not Bonito's Postgres — evaluated for Phase 3)
  - Pre-warms sentence-transformers model at startup to avoid first-request latency
- **Model Tier Gating** — Memory budget scales by model capability
  - Zero budget (no memory): flash, mini, haiku, kimi, gemma models + `auto` routing
  - Full budget (1000 tokens): opus, sonnet, gpt-4o, and other large models
  - Prevents small models from hallucinating on injected memory context
- **Non-Fatal Design** — All Memwright operations wrapped in try/except
  - Recall failure returns empty string (no memory section in prompt)
  - Store failure is logged but does not block response delivery
  - Async wrappers via `asyncio.to_thread` prevent blocking the event loop
- **New file**: `backend/app/services/memwright_service.py`
- **23 new tests**: `backend/tests/test_memwright_integration.py` covering regression, recall, store, tier gating, session isolation, and performance

### Added - Org Secrets Store
- **Secure Key-Value Storage** — Org-scoped secrets backed by HashiCorp Vault
  - 5 API endpoints: create, list, get, update, delete
  - 4 CLI commands: `bonito secrets list/get/set/delete`
  - YAML support in `bonito deploy` with validation warnings
  - Runtime injection into agent system prompts via `_resolve_secrets()`
  - Full documentation: `docs/SECRETS.md`

### Added - VectorBoost (KB Compression)
- **Adaptive Vector Compression** — 3.9x to 8x storage reduction for knowledge base embeddings
  - 3 compression methods: scalar-8bit (recommended), polar-8bit, polar-4bit
  - API endpoints: GET/PUT `/api/kb/{kb_id}/config`
  - CLI: `bonito kb config <kb> [--compression <method>]`
  - YAML support in knowledge base declarations
  - Research benchmarks: PolarQuant vs TurboQuant vs Lloyd-Max quantizer
  - Full documentation: `docs/VECTORBOOST.md`

### Technical Implementation
- **Database**: Migrations 034 (org_secrets table) and 035 (agent secrets + KB compression columns)
- **Dependencies**: Added `memwright>=0.1.0` to requirements
- **No breaking changes**: Existing agent memory service, delegation, background tasks, and approval workflows untouched

## [2.3.0] - 2026-03-21

### Added - Documentation & Integrations

- **Documentation Overhaul**
  - Added 6 new sections to docs page (getbonito.com/docs)
  - Direct Providers: OpenAI, Anthropic, Groq now documented alongside AWS/Azure/GCP
  - Cross-Region Inference: automatic Bedrock region failover documentation
  - Model Aliases: provider-agnostic model references
  - Declarative Config: full bonito.yaml examples (AWS Bedrock stack + multi-provider stack)
  - Code Review: GitHub App integration documentation
  - OpenClaw Integration: workstation workflow with skill install

- **OpenClaw Skill (ClaHub)**
  - Published `bonito` skill to ClaHub (clawhub.ai)
  - Conversational onboarding for new users
  - Health check and prerequisite verification scripts
  - Install: `npx clawhub@latest install bonito`

- **Updated Provider Coverage**
  - Getting Started now reflects all 6 supported providers
  - Provider Setup includes OpenAI Direct, Anthropic Direct, and Groq sections

## [2.2.0] - 2026-03-12

### Added - Gateway Intelligence

- **Auto Cross-Region Inference Profiles (AWS Bedrock)**
  - Gateway automatically detects newer Bedrock models that require cross-region inference profiles
  - Transparently prepends `us.` prefix for models like Claude Sonnet 4, Opus 4, Llama 3.3/4, Mistral Large 2
  - Customers register canonical model IDs (e.g. `anthropic.claude-sonnet-4-20250514-v1:0`); the gateway handles routing
  - Shared `_apply_bedrock_inference_profile()` function used across gateway routing and model test endpoints
  - Prefix list: Claude Sonnet 4, Opus 4, Haiku 4, Claude 3.7, Claude 3.5 Sonnet v2, Claude 3.5 Haiku, Llama 3.2/3.3/4, Mistral Large 2
  - Zero customer-facing changes when AWS updates inference profile requirements

- **Intelligent Multi-Provider Failover**
  - Broadened failover triggers beyond rate limits (429) to cover:
    - Timeouts and deadline exceeded errors
    - Server errors (500, 502, 503, 529)
    - Overloaded/capacity provider errors
    - Model unavailability and deployment-not-found errors
  - New `_is_retriable_provider_error()` detection function
  - Failover attempts are logged with accurate error categories (`rate_limited` vs `provider_error`)
  - Response metadata includes failover details (`bonito.failover.reason`, `original_model`, `routed_to`)
  - Added Claude Sonnet 4 to cross-provider model equivalence map (Anthropic Direct <-> AWS Bedrock)
  - Model equivalence map now covers: Claude Sonnet 4, Claude 3.5 Sonnet, Claude 3 Haiku, Llama 3.3/3.1 70B, Llama 3.1 8B, Mixtral 8x7B, Gemma2 9B

### Changed
- Provider count updated from 3 to 6 (AWS Bedrock, Azure OpenAI, GCP Vertex AI, OpenAI, Anthropic, Groq)
- Competitor comparison table updated with Guild.ai and new differentiator columns

## [2.1.0] - 2026-03-09

### Added - Bonobot Enterprise Features
- **Persistent Agent Memory System**
  - Long-term memory storage with pgvector similarity search
  - Five memory types: fact, pattern, interaction, preference, context  
  - AI-powered memory extraction from conversation sessions
  - Vector similarity search with configurable importance scoring
  - Memory statistics and analytics
  - 7 new API endpoints for memory management

- **Scheduled Autonomous Execution**
  - Cron expression-based task scheduling with timezone support
  - Automated task execution with configurable prompts
  - Multi-channel output delivery (webhook, email, Slack, dashboard)
  - Execution history tracking with success/failure logging
  - Retry logic with configurable delays and timeouts
  - Manual schedule triggering for testing and immediate execution
  - 8 new API endpoints for schedule management

- **Approval Queue / Human-in-the-Loop**
  - Configurable approval requirements per agent and action type
  - Risk level assessment (low, medium, high, critical) with automated classification
  - Auto-approval conditions based on configurable rules
  - Manual approval/rejection workflow with review notes
  - Timeout handling with automatic expiration of pending actions
  - Comprehensive approval history and queue management
  - Role-based approval permissions preparation
  - 11 new API endpoints for approval workflow management

### Technical Implementation
- **Database Schema**: Three new migration files with proper indexing
  - `40771788af6d_add_agent_memory_tables.py` - Agent memory with vector search
  - `cfc22bba5dd4_add_scheduled_execution_tables.py` - Scheduling infrastructure
  - `0b1b3e3d1a88_add_approval_queue_tables.py` - Approval workflow
- **Performance**: Sub-5ms response times across all enterprise endpoints
- **Integration**: Seamless integration with existing agent engine and security framework
- **Dependencies**: Added croniter and pytz for robust scheduling support

## [2.0.5] - 2026-03-05

### Added
- **AWS Infrastructure Generators and Onboarding Wizard**
  - Terraform, Pulumi, and CloudFormation template generation
  - AWS Bedrock IAM policy automation with least-privilege access
  - Step-by-step onboarding flow with credential validation
  - Support for multiple AWS regions and account configurations

- **AWS Bedrock Model Access Detection and Credential Management**
  - Automatic detection of available Bedrock models based on region
  - Enhanced credential validation with detailed error reporting  
  - Database migration 029 for improved AWS provider metadata
  - Real-time model availability checking

### Changed
- **Free Tier Increase**: Bumped free tier from 1,000 to 5,000 API calls per month
- **Navigation Enhancement**: Added Compare page to main navigation and footer
- **Documentation Updates**: Comprehensive fixes and improvements across all documentation

### Removed
- **Compliance Claims**: Removed false SOC2 and HIPAA compliance statements pending certification

### Fixed
- AWS Bedrock authentication flow edge cases
- Provider credential storage and retrieval optimization
- Model availability caching improvements
- Documentation accuracy and consistency issues

## [2.0.0] - 2026-02-22

### Added - Bonobot v1 Launch
- **AI Agent Framework**: Enterprise-grade agent system with visual canvas
- **Agent Canvas**: React Flow-based visual agent management interface
- **Built-in Tools**: Knowledge base search, HTTP requests, agent-to-agent invocation
- **Enterprise Security**: Default deny policies, budget enforcement, rate limiting, SSRF protection
- **Audit Trail**: Comprehensive logging for all agent actions and decisions
- **Project Organization**: Multi-project agent management with team access controls

### Added - SAML SSO
- **Enterprise Single Sign-On**: SAML 2.0 implementation
- **Provider Support**: Okta, Azure AD, Google Workspace, and custom SAML providers
- **SSO Enforcement**: Organization-wide SSO requirement with break-glass admin access
- **Just-in-Time Provisioning**: Automatic user creation and role assignment

### Added - AI Context (Knowledge Base)
- **Cross-Cloud RAG Pipeline**: Vendor-neutral knowledge system
- **Document Processing**: Upload, parse, chunk, and embed company documents
- **Vector Search**: pgvector-powered similarity search with HNSW indexing
- **Gateway Integration**: Automatic context injection into LLM queries
- **Source Citations**: Traceable knowledge references in agent responses

## [1.5.0] - 2026-01-15

### Added
- **Cost Intelligence**: Real-time cost aggregation and forecasting
- **Compliance Engine**: SOC-2, HIPAA, and GDPR policy checking framework
- **Multi-Cloud Gateway**: OpenAI-compatible API proxy with intelligent routing
- **AI Copilot**: Groq-powered operations assistant for platform management

### Changed
- **Database Migration**: Upgraded to PostgreSQL 18.2 with pgvector extension
- **Performance**: Optimized vector search operations and query patterns

## [1.0.0] - 2026-01-01

### Added
- **Core Platform**: Multi-cloud AI operations management
- **Cloud Integrations**: AWS Bedrock, Azure AI Foundry, Google Vertex AI
- **Role-Based Access Control**: Team management with granular permissions
- **Provider Management**: Unified dashboard for all cloud AI providers
- **Audit Logging**: Comprehensive action tracking and compliance reporting

---

## Legend

- **Added** for new features
- **Changed** for changes in existing functionality  
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for vulnerability fixes