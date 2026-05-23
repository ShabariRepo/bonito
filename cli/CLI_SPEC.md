# Bonito CLI — Design Spec

## Overview
`bonito` is a CLI tool that gives enterprise AI teams a unified command-line interface 
to manage multi-cloud AI workloads through the Bonito platform. Instead of juggling 
`aws bedrock`, `az cognitiveservices`, and `gcloud ai`, teams use one tool.

## Install
```bash
pip install bonito-cli
```

## Tech Stack
- **Python 3.10+** with **Typer** (CLI framework, auto-help, auto-completion)
- **Rich** for beautiful terminal output (tables, panels, progress bars, syntax highlighting)
- **httpx** for async HTTP calls to the Bonito API
- **keyring** (optional) for secure credential storage, fallback to file-based config

## Config Storage
- `~/.bonito/config.json` — API endpoint, default org, preferences
- `~/.bonito/credentials.json` — API key (or use env var `BONITO_API_KEY`)
- Environment variables override file config:
  - `BONITO_API_KEY` — API key
  - `BONITO_API_URL` — API endpoint (default: `https://celebrated-contentment-production-0fc4.up.railway.app`)

## Authentication Flow
Users sign up on the Bonito web app, then:
```bash
bonito auth login                    # Prompts for email + password
bonito auth login --email admin@co   # Direct email auth
bonito auth whoami                   # Show current user
bonito auth status                   # Check auth status + API connectivity
bonito auth logout                   # Clear stored credentials
```

## Command Structure

### `bonito auth` — Authentication & Account Management
```bash
bonito auth login [--email E] [--password P] [--api-url URL]
bonito auth logout
bonito auth whoami
bonito auth status
```

### `bonito providers` — Cloud Provider Management
```bash
bonito providers list [--json]
bonito providers status PROVIDER_ID [--json]
bonito providers add aws [--access-key X] [--secret-key Y] [--region R]
bonito providers add azure [--tenant-id X] [--client-id Y] [--client-secret Z] [--subscription-id S] [--endpoint E]
bonito providers add gcp [--project-id X] [--service-account-json PATH] [--region R]
bonito providers test PROVIDER_ID [--json]
bonito providers remove PROVIDER_ID [--force] [--json]
```

### `bonito models` — Model Management
```bash
bonito models list [--provider TYPE] [--search QUERY] [--json]
bonito models search QUERY [--provider TYPE] [--json]
bonito models info MODEL_ID [--json]
bonito models enable MODEL_ID [MODEL_ID...] [--json]     # single or bulk activate
bonito models sync [--provider PROVIDER_ID] [--json]
```

### `bonito chat` — Interactive AI Chat (Playground)
```bash
bonito chat                                    # Interactive chat (picks default model)
bonito chat -m MODEL_ID                        # Chat with specific model
bonito chat -m MODEL_ID --temperature 0.3      # With parameters
bonito chat --compare MODEL1 --compare MODEL2  # Compare mode
echo "Summarize this" | bonito chat -m MODEL   # Pipe input
bonito chat -m MODEL "What is 2+2?"            # One-shot (non-interactive)
```

Interactive slash commands: `/model`, `/temp`, `/tokens`, `/clear`, `/export`, `/stats`, `/quit`

### `bonito gateway` — API Gateway Management
```bash
bonito gateway status [--json]
bonito gateway usage [--days N] [--json]
bonito gateway logs [--limit N] [--model M] [--json]
bonito gateway keys list [--json]
bonito gateway keys create [--name N] [--json]
bonito gateway keys revoke KEY_ID [--force] [--json]
bonito gateway config show [--json]
bonito gateway config set FIELD VALUE [--json]
```

### `bonito policies` — Routing Policies
```bash
bonito policies list [--json]
bonito policies create [--name N] [--strategy S] [--models M1,M2] [--json]
bonito policies info POLICY_ID [--json]
bonito policies test POLICY_ID "test prompt" [--json]
bonito policies stats POLICY_ID [--json]
bonito policies delete POLICY_ID [--force] [--json]
```

Strategies: `cost_optimized`, `latency_optimized`, `quality_optimized`, `round_robin`

### `bonito analytics` — Usage Analytics & Costs
```bash
bonito analytics overview [--json]
bonito analytics usage [--period day|week|month] [--json]
bonito analytics costs [--period daily|weekly|monthly] [--json]
bonito analytics trends [--json]
bonito analytics digest [--json]
```

### `bonito agents` — Bonobot Agent Management
```bash
bonito agents list [--project PROJECT_ID] [--json]
bonito agents create --project PROJECT_ID --name NAME [--description DESC] [--prompt PROMPT] [--prompt-file FILE] [--model MODEL] [--max-turns N] [--timeout SECS] [--rate-limit RPM] [--json]
bonito agents info AGENT_ID [--sessions] [--json]
bonito agents update AGENT_ID [--name NAME] [--description DESC] [--model MODEL] [--max-turns N] [--timeout SECS] [--rate-limit RPM] [--status STATUS] [--json]
bonito agents delete AGENT_ID [--force] 
bonito agents execute AGENT_ID [MESSAGE] [--session SESSION_ID] [--parent-agent PARENT_AGENT_ID] [--json]
bonito agents sessions AGENT_ID [--limit N] [--json]
bonito agents messages AGENT_ID SESSION_ID [--json]
bonito agents connections AGENT_ID [--json]
bonito agents triggers AGENT_ID [--json]
```

### `bonito projects` — Agent Project Management
```bash
bonito projects list [--json]
bonito projects create --name NAME [--description DESC] [--budget AMOUNT] [--json]
bonito projects info PROJECT_ID [--json]
bonito projects update PROJECT_ID [--name NAME] [--description DESC] [--budget AMOUNT] [--status STATUS] [--json]
bonito projects delete PROJECT_ID [--force]
bonito projects graph PROJECT_ID [--output FILE] [--json]
```

### `bonito groups` — Agent Group Management (RBAC)
```bash
bonito groups list [--project PROJECT_ID] [--json]
bonito groups create --project PROJECT_ID --name NAME [--description DESC] [--budget AMOUNT] [--json]
bonito groups info GROUP_ID [--json]
bonito groups update GROUP_ID [--name NAME] [--description DESC] [--budget AMOUNT] [--json]
bonito groups delete GROUP_ID [--force]
bonito groups assign GROUP_ID AGENT_ID
bonito groups unassign AGENT_ID
```

### `bonito sso` — SAML Single Sign-On Management
```bash
bonito sso config [--json]
bonito sso setup [--provider TYPE] [--sso-url URL] [--entity-id ID] [--metadata-url URL] [--cert-file FILE] [--interactive/--non-interactive] [--json]
bonito sso test
bonito sso enable
bonito sso enforce [--breakglass-admin USER_ID]
bonito sso disable
bonito sso status [--email EMAIL]
```

### `bonito deployments` — Deployment Management
```bash
bonito deployments list [--json]
bonito deployments create [--model M] [--name N] [--search S] [--units U] [--tpm T] [--tier TIER] [--json]
bonito deployments status DEPLOYMENT_ID [--json]
bonito deployments delete DEPLOYMENT_ID [--force] [--json]
```

### `bonito kb` — Knowledge Base / AI Context (RAG)
```bash
bonito kb list [--json]                                        # List all knowledge bases
bonito kb create [--name N] [--description D] [--source TYPE]  # Create a knowledge base
bonito kb info KB_ID [--json]                                  # Show KB details + stats
bonito kb upload KB_ID FILE [FILE...] [--json]                 # Upload documents
bonito kb documents KB_ID [--json]                             # List documents in a KB
bonito kb search KB_ID "query" [--top-k K] [--json]            # Semantic search
bonito kb delete KB_ID [--force] [--json]                      # Delete a knowledge base
bonito kb delete-doc KB_ID DOC_ID [--force] [--json]           # Delete a document
bonito kb sync KB_ID [--force] [--json]                        # Trigger cloud storage sync
bonito kb sync-status KB_ID [--json]                           # Check sync progress
bonito kb stats KB_ID [--json]                                 # Show KB statistics
```

Source types: `upload` (default), `s3`, `azure_blob`, `gcs`

Supported file formats: PDF, DOCX, TXT, MD, HTML, CSV, JSON (max 50MB)

## Output Formatting
- Default: Rich-formatted tables, panels, and styled text
- `--json` flag on any command: raw JSON output (for piping/scripting)
- Color auto-detection (disable with `NO_COLOR=1`)

## Interactive Chat UX
```
╭─ 🐟 Bonito Chat ─────────────────────────────────╮
│ Model: claude-3-sonnet (AWS Bedrock)               │
│ Temperature: 0.7 │ Max Tokens: 1000               │
╰────────────────────────────────────────────────────╯

You: What are the main differences between transformers and RNNs?

Claude 3 Sonnet: Transformers and RNNs differ in several key ways...
  ── 847 tokens · $0.0042 · 1.2s

You: /help
Commands: /model <id>  /temp <0-2>  /tokens <n>  /clear  /export  /stats  /quit

You: /quit
Session: 45s · 3 messages · 2.8K tokens · $0.012
```

## Error Handling
- Clear error messages with suggested fixes
- Pydantic 422 validation errors parsed into friendly messages
- Retry logic for transient failures (network timeouts, rate limits)
- All auth-required commands check credentials and suggest `bonito auth login`

## API Endpoint Reference
The CLI talks to the existing Bonito backend. Key endpoints:

### Auth
- POST /api/auth/login → TokenResponse
- GET /api/auth/me → UserResponse

### Providers
- GET /api/providers/ → List[ProviderResponse]
- POST /api/providers/connect → ProviderResponse
- POST /api/providers/{id}/verify → VerifyResponse
- DELETE /api/providers/{id}
- GET /api/providers/{id}/summary → ProviderSummary

### Models
- GET /api/models/ → List[ModelResponse]
- GET /api/models/{id} → ModelResponse
- GET /api/models/{id}/details → ModelDetailsResponse
- POST /api/models/{id}/playground → PlaygroundResponse
- POST /api/models/{id}/activate
- POST /api/models/activate-bulk
- POST /api/models/sync

### Gateway
- GET /api/gateway/keys → List[GatewayKeyResponse]
- POST /api/gateway/keys → GatewayKeyCreated
- DELETE /api/gateway/keys/{id}
- GET /api/gateway/logs → List[GatewayLogEntry]
- GET /api/gateway/config → GatewayConfigResponse
- PUT /api/gateway/config → GatewayConfigResponse
- GET /api/gateway/usage → UsageSummary

### Routing Policies
- GET /api/routing-policies/ → List[RoutingPolicyResponse]
- POST /api/routing-policies/ → RoutingPolicyResponse
- GET /api/routing-policies/{id} → RoutingPolicyDetailResponse
- PUT /api/routing-policies/{id}
- DELETE /api/routing-policies/{id}
- POST /api/routing-policies/{id}/test → PolicyTestResult
- GET /api/routing-policies/{id}/stats → PolicyStats

### Deployments
- GET /api/deployments/ → List[DeploymentResponse]
- POST /api/deployments/ → DeploymentResponse
- POST /api/deployments/{id}/status → StatusResponse
- DELETE /api/deployments/{id}

### Analytics
- GET /api/analytics/overview
- GET /api/analytics/usage?period=day|week|month
- GET /api/analytics/costs
- GET /api/analytics/trends
- GET /api/analytics/digest

### Knowledge Bases (RAG)
- GET /api/knowledge-bases → List[KnowledgeBaseResponse]
- POST /api/knowledge-bases → KnowledgeBaseResponse
- GET /api/knowledge-bases/{kb_id} → KnowledgeBaseResponse
- PUT /api/knowledge-bases/{kb_id} → KnowledgeBaseResponse
- DELETE /api/knowledge-bases/{kb_id}
- GET /api/knowledge-bases/{kb_id}/documents → List[KBDocumentResponse]
- POST /api/knowledge-bases/{kb_id}/documents (multipart upload)
- DELETE /api/knowledge-bases/{kb_id}/documents/{doc_id}
- POST /api/knowledge-bases/{kb_id}/sync → KBSyncStatus
- GET /api/knowledge-bases/{kb_id}/sync-status → KBSyncStatus
- POST /api/knowledge-bases/{kb_id}/search → KBSearchResponse
- GET /api/knowledge-bases/{kb_id}/stats → KBStats

### Bonobot Agents
- GET /api/projects/{project_id}/agents → List[AgentResponse]
- POST /api/projects/{project_id}/agents → AgentResponse
- GET /api/agents/{agent_id} → AgentDetailResponse
- PUT /api/agents/{agent_id} → AgentResponse
- DELETE /api/agents/{agent_id}
- POST /api/agents/{agent_id}/execute → AgentExecuteResponse
- GET /api/agents/{agent_id}/sessions → List[AgentSessionResponse]
- GET /api/agents/{agent_id}/sessions/{session_id}/messages → List[AgentMessageResponse]
- GET /api/agents/{agent_id}/connections → List[AgentConnectionResponse]
- POST /api/agents/{agent_id}/connections → AgentConnectionResponse
- DELETE /api/connections/{connection_id}
- GET /api/agents/{agent_id}/triggers → List[AgentTriggerResponse]
- POST /api/agents/{agent_id}/triggers → AgentTriggerResponse
- DELETE /api/triggers/{trigger_id}

### Projects
- GET /api/projects → List[ProjectResponse]
- POST /api/projects → ProjectResponse
- GET /api/projects/{project_id} → ProjectResponse
- PUT /api/projects/{project_id} → ProjectResponse
- DELETE /api/projects/{project_id}
- GET /api/projects/{project_id}/graph → ProjectGraphResponse

### Agent Groups (RBAC)
- GET /api/groups → List[AgentGroupResponse]
- POST /api/groups → AgentGroupResponse
- GET /api/groups/{group_id} → AgentGroupResponse
- PUT /api/groups/{group_id} → AgentGroupResponse
- DELETE /api/groups/{group_id}
- GET /api/projects/{project_id}/groups → List[AgentGroupResponse]

### SSO/SAML
- GET /api/sso/config → SSOConfigResponse
- PUT /api/sso/config → SSOConfigResponse
- POST /api/sso/test → SSOTestResult
- POST /api/sso/enable → SSOStatusResult
- POST /api/sso/enforce → SSOStatusResult
- POST /api/sso/disable → SSOStatusResult
- POST /api/auth/saml/check-sso → SSOStatusResponse
- GET /api/auth/saml/{org_id}/metadata (XML)
- GET /api/auth/saml/{org_id}/login → Redirect
- POST /api/auth/saml/{org_id}/acs → Redirect
- GET /api/auth/saml/{org_id}/slo → Redirect

### Health
- GET /api/health
- GET /api/health/ready

## File Structure
```
cli/
├── pyproject.toml           # Package config, entry point
├── CLI_SPEC.md              # This file
├── CHANGELOG.md             # Version history
├── README.md                # CLI documentation
├── bonito_cli/
│   ├── __init__.py          # Version
│   ├── __main__.py          # python -m bonito_cli
│   ├── app.py               # Main Typer app, register subcommands
│   ├── config.py            # Config file management (~/.bonito/)
│   ├── api.py               # HTTP client (httpx) wrapper
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── auth.py          # auth login/logout/whoami/status
│   │   ├── providers.py     # providers list/status/add/test/remove
│   │   ├── models.py        # models list/search/info/enable/sync
│   │   ├── chat.py          # Interactive chat + one-shot + compare
│   │   ├── gateway.py       # gateway status/usage/logs/keys/config
│   │   ├── policies.py      # routing policies CRUD + test + stats
│   │   ├── analytics.py     # analytics overview/usage/costs/trends/digest
│   │   ├── deployments.py   # deployment list/create/status/delete
│   │   └── kb.py            # knowledge base CRUD + upload + search + sync
│   └── utils/
│       ├── __init__.py
│       ├── display.py       # Rich formatting helpers (tables, panels, etc.)
│       └── auth.py          # Token refresh, credential storage
```

## Version History
See [CHANGELOG.md](CHANGELOG.md) for details.

- **0.2.0** — Knowledge base (RAG) commands, deployment commands, bug fixes
- **0.1.0** — Initial release: auth, providers, models, chat, gateway, policies, analytics
