# /bonito:create-agent

Create a new BonBon or Bonobot agent on the Bonito platform.

## Usage

```
/bonito:create-agent <name> --model <model> [--type bonbon|bonobot] [--prompt "system prompt"]
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `name` | Yes | – | Agent name |
| `--model` | Yes | – | Model to use (e.g. `gpt-4o`, `claude-sonnet-4-20250514`) |
| `--type` | No | `bonbon` | Agent type: `bonbon` (single model) or `bonobot` (orchestrator) |
| `--prompt` | No | – | System prompt for the agent |
| `--project` | No | default | Project ID to create the agent in |

## Examples

```
/bonito:create-agent my-assistant --model gpt-4o --prompt "You are a helpful coding assistant."
```

```
/bonito:create-agent orchestrator --model claude-sonnet-4-20250514 --type bonobot
```

## Agent Types

- **BonBon**: Single-model agent. Simple, fast, good for focused tasks.
- **Bonobot**: Multi-model orchestrator. Routes to the best model per subtask. Choose from Free, Standard, or Premium tiers.
