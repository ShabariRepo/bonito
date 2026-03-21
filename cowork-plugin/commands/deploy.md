# /bonito:deploy

Deploy a `bonito.yaml` configuration to the Bonito platform.

## Usage

```
/bonito:deploy [path-to-bonito.yaml]
```

## What it does

1. Reads the `bonito.yaml` file (defaults to `./bonito.yaml` in the current directory)
2. Validates the configuration structure
3. Connects any new providers specified in the config
4. Syncs and activates the specified models
5. Creates or updates agents defined in the config
6. Reports the deployment status

## Example bonito.yaml

```yaml
providers:
  - type: openai
    credentials:
      api_key: $OPENAI_API_KEY
  - type: anthropic
    credentials:
      api_key: $ANTHROPIC_API_KEY

models:
  - gpt-4o
  - claude-sonnet-4-20250514

agents:
  - name: support-bot
    type: bonbon
    model: gpt-4o
    system_prompt: "You are a helpful support assistant."
```

## Notes

- Environment variables in credentials (prefixed with `$`) are resolved at deploy time
- Existing providers are skipped (matched by type)
- Agents are created if they don't exist, or updated if the name matches
