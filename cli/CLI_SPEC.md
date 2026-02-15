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
  - `BONITO_API_URL` — API endpoint (default: `https://getbonito.com/api`)

## Authentication Flow
Users sign up on the Bonito web app, then:
```bash
bonito auth login                    # Opens browser for OAuth, or prompts for API key
bonito auth login --api-key bk-xxx   # Direct API key auth
bonito auth status                   # Show current auth state + org info
bonito auth logout                   # Clear stored credentials
```

## Command Structure

### `bonito auth` — Authentication & API Keys
```bash
bonito auth login [--api-key KEY]    # Authenticate (browser OAuth or API key)
bonito auth logout                   # Clear credentials
bonito auth status                   # Show auth status, org, user info
bonito auth keys list                # List API/gateway keys
bonito auth keys create [--name N]   # Create new gateway key
bonito auth keys revoke KEY_ID       # Revoke a key
```

### `bonito providers` — Cloud Provider Management
```bash
bonito providers list                          # List connected providers
bonito providers add aws --access-key X --secret-key Y --region us-east-1
bonito providers add azure --tenant-id X --client-id Y --client-secret Z --subscription-id S --endpoint E
bonito providers add gcp --project-id X --service-account-json path/to/sa.json --region us-central1
bonito providers test PROVIDER_ID              # Verify credentials
bonito providers remove PROVIDER_ID            # Disconnect provider
bonito providers models PROVIDER_ID            # List models for a provider
bonito providers costs PROVIDER_ID [--days 30] # Show provider costs
```

### `bonito models` — Model Management
```bash
bonito models list [--provider aws] [--enabled-only] [--search QUERY]
bonito models info MODEL_ID                    # Detailed model info (pricing, capabilities, status)
bonito models enable MODEL_ID                  # Activate model on cloud account
bonito models enable --bulk ID1 ID2 ID3        # Bulk activate
bonito models sync [--provider PROVIDER_ID]    # Sync model catalog from cloud
```

### `bonito chat` — Interactive AI Chat (Playground)
```bash
bonito chat                                    # Interactive chat (picks default model)
bonito chat -m claude-3-sonnet                 # Chat with specific model
bonito chat -m gpt-4o --temperature 0.3        # With parameters
bonito chat --compare model1 model2            # Compare mode
echo "Summarize this" | bonito chat -m claude  # Pipe input
bonito chat -m claude "What is 2+2?"           # One-shot (non-interactive)
```

### `bonito gateway` — API Gateway Management
```bash
bonito gateway status                          # Gateway health + config
bonito gateway keys list                       # List gateway API keys
bonito gateway keys create [--name N]          # Create key
bonito gateway keys revoke KEY_ID              # Revoke key
bonito gateway logs [--limit 50] [--model X]   # View recent gateway logs
bonito gateway config                          # Show gateway config
bonito gateway config set FIELD VALUE          # Update gateway config
```

### `bonito policies` — Routing Policies
```bash
bonito policies list                           # List routing policies
bonito policies create --name N --strategy cost_optimized --models M1,M2
bonito policies info POLICY_ID                 # Policy details + stats
bonito policies test POLICY_ID "test prompt"   # Dry-run test
bonito policies toggle POLICY_ID               # Enable/disable
bonito policies delete POLICY_ID               # Delete policy
```

### `bonito analytics` — Usage Analytics & Costs
```bash
bonito analytics overview                      # Dashboard summary (requests, cost, top model)
bonito analytics usage [--period day|week|month]  # Usage over time
bonito analytics costs [--period daily|weekly|monthly]  # Cost breakdown
bonito analytics trends                        # Trend analysis
bonito analytics digest                        # Weekly digest
```

### `bonito costs` — Cloud Cost Intelligence
```bash
bonito costs summary [--period monthly]        # Total spend across providers
bonito costs breakdown                         # By provider, model, department
bonito costs forecast                          # 14-day cost forecast
bonito costs recommendations                   # Optimization recommendations
bonito costs export [--format csv]             # Export cost data
```

### `bonito config` — CLI Configuration
```bash
bonito config show                             # Show current config
bonito config set api_url https://...          # Set API endpoint
bonito config set default_model claude-3-sonnet  # Set default model
bonito config reset                            # Reset to defaults
```

### `bonito completion` — Shell Completions
```bash
bonito completion install bash                 # Install bash completions
bonito completion install zsh                  # Install zsh completions
bonito completion install fish                 # Install fish completions
```

## Output Formatting
- Default: Rich-formatted tables, panels, and styled text
- `--json` flag on any command: raw JSON output (for piping/scripting)
- `--quiet` flag: minimal output (for CI/CD)
- Color auto-detection (disable with `--no-color` or `NO_COLOR=1`)

## Interactive Chat UX
```
╭─ Bonito Chat ─────────────────────────────────────╮
│ Model: claude-3-sonnet (AWS Bedrock)               │
│ Temperature: 0.7 │ Max Tokens: 1000               │
╰────────────────────────────────────────────────────╯

You: What are the main differences between transformers and RNNs?

Claude 3 Sonnet: Transformers and RNNs differ in several key ways...
[tokens: 847 | cost: $0.0042 | latency: 1.2s]

You: /help
Commands: /model <name>, /temp <0-2>, /tokens <n>, /clear, /export, /quit

You: /quit
Session saved. Total: 3 messages, $0.012, 2847 tokens.
```

## Error Handling
- Clear error messages with suggested fixes
- `bonito doctor` command to diagnose common issues (connectivity, auth, provider status)
- Retry logic for transient failures (network timeouts, rate limits)

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
- GET /api/providers/{id}/models → List[ModelInfo]
- GET /api/providers/{id}/costs → CostDataResponse

### Models
- GET /api/models/ → List[ModelResponse]
- GET /api/models/{id} → ModelResponse
- GET /api/models/{id}/details → ModelDetailsResponse
- POST /api/models/{id}/playground → PlaygroundResponse
- POST /api/models/compare → CompareResponse
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

### Gateway Proxy (OpenAI-compatible)
- POST /v1/chat/completions
- POST /v1/completions
- POST /v1/embeddings
- GET /v1/models

### Routing Policies
- GET /api/routing-policies/ → List[RoutingPolicyResponse]
- POST /api/routing-policies/ → RoutingPolicyResponse
- GET /api/routing-policies/{id} → RoutingPolicyDetailResponse
- PUT /api/routing-policies/{id}
- DELETE /api/routing-policies/{id}
- POST /api/routing-policies/{id}/test → PolicyTestResult
- GET /api/routing-policies/{id}/stats → PolicyStats

### Analytics
- GET /api/analytics/overview
- GET /api/analytics/usage?period=day|week|month
- GET /api/analytics/costs
- GET /api/analytics/trends
- GET /api/analytics/digest

### Costs
- GET /api/costs/?period=daily|weekly|monthly
- GET /api/costs/breakdown
- GET /api/costs/forecast
- GET /api/costs/recommendations

### Health
- GET /api/health
- GET /api/health/ready

## File Structure
```
cli/
├── pyproject.toml           # Package config, entry point
├── README.md                # CLI documentation
├── bonito_cli/
│   ├── __init__.py          # Version
│   ├── __main__.py          # python -m bonito_cli
│   ├── app.py               # Main Typer app, register subcommands
│   ├── config.py            # Config file management (~/.bonito/)
│   ├── api.py               # HTTP client (httpx) wrapper
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── auth.py          # auth login/logout/status/keys
│   │   ├── providers.py     # providers list/add/test/remove
│   │   ├── models.py        # models list/info/enable/sync
│   │   ├── chat.py          # Interactive chat + one-shot
│   │   ├── gateway.py       # gateway status/keys/logs/config
│   │   ├── policies.py      # routing policies CRUD + test
│   │   ├── analytics.py     # analytics overview/usage/costs/trends
│   │   ├── costs.py         # cost intelligence
│   │   └── config_cmd.py    # CLI config management
│   └── utils/
│       ├── __init__.py
│       ├── display.py       # Rich formatting helpers (tables, panels, etc.)
│       └── auth.py          # Token refresh, credential storage
```

## Notes
- The CLI must work with the EXISTING backend API — no new backend endpoints needed
- Auth tokens: store access_token + refresh_token, auto-refresh on 401
- All commands that require auth should check credentials first and give clear "run bonito auth login" messages
- The `bonito chat` interactive mode is the killer feature — make it feel great
- Support piping: `cat file.txt | bonito chat -m claude "Summarize this"`
- The `--json` flag is critical for CI/CD automation
