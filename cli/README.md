# Bonito CLI

🍌 Unified multi-cloud AI management from your terminal.

Bonito CLI gives enterprise AI teams a single command-line interface to manage models, deployments, costs, and workloads across AWS Bedrock, Azure OpenAI, Google Vertex AI, and more.

## Installation

```bash
pip install bonito-cli
```

Or install from source:

```bash
git clone https://github.com/ShabariRepo/bonito.git
cd bonito/cli
pip install -e .
```

## Quick Start

1. **Authenticate** with your Bonito API key:
   ```bash
   bonito auth login
   ```

2. **List available models**:
   ```bash
   bonito models list
   ```

3. **Start an interactive chat**:
   ```bash
   bonito chat
   ```

4. **Create a deployment**:
   ```bash
   bonito deployments create
   ```

## Commands

- `bonito auth` - Authentication and API key management
- `bonito providers` - Cloud provider management
- `bonito models` - AI model management
- `bonito deployments` - Deployment management
- `bonito chat` - Interactive AI chat
- `bonito gateway` - API Gateway management
- `bonito analytics` - Usage analytics
- `bonito policies` - Routing policies

## Configuration

Configuration is stored in `~/.bonito/config.json`:
- API URL (defaults to production)
- Default model preferences
- Output formatting options

Credentials are stored securely in `~/.bonito/credentials.json`.

## Environment Variables

- `BONITO_API_KEY` - Your Bonito API key
- `BONITO_API_URL` - Custom API endpoint

## Examples

```bash
# Interactive chat with specific model
bonito chat -m claude-3-sonnet

# One-shot completion
bonito chat "Explain quantum computing"

# Compare multiple models
bonito chat --compare gpt-4o claude-3-sonnet "What is AI?"

# List deployments
bonito deployments list

# Gateway status
bonito gateway status

# Usage analytics
bonito analytics usage --period week
```

For detailed help on any command:

```bash
bonito <command> --help
```

## License

MIT License. See LICENSE file for details.