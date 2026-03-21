# /bonito:test-gateway

Send a test request through the Bonito gateway to verify connectivity and routing.

## Usage

```
/bonito:test-gateway [--model <model>] [--message "your test message"]
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--model` | No | `gpt-4o` | Model to test with |
| `--message` | No | `"Hello, this is a test."` | Test message to send |

## What it does

1. Sends a chat completion request through the Bonito gateway
2. Measures response time
3. Displays:
   - Model used (including any alias resolution)
   - Response content
   - Latency (ms)
   - Token usage (prompt / completion / total)
   - Provider that served the request

## Example

```
/bonito:test-gateway --model claude-sonnet-4-20250514 --message "What is 2+2?"
```

## Notes

- This uses your real API quota — each test consumes tokens
- Great for verifying that a newly connected provider is working
- Use after `/bonito:deploy` to confirm the setup
