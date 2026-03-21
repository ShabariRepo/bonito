# Gateway Routing

The Bonito gateway is an OpenAI-compatible API that routes requests across multiple AI providers.

## Endpoint

```
POST https://api.getbonito.com/v1/chat/completions
Authorization: Bearer $BONITO_API_KEY
```

Drop-in replacement for OpenAI — just change the base URL.

## Routing Policies

### Cost-Optimized
Routes to the cheapest provider that supports the requested model. If `gpt-4o` is available on both OpenAI and Azure, picks the one with lower per-token cost.

### Latency-Optimized
Routes to the provider with the lowest observed latency. Uses historical response times to make decisions.

### Round-Robin
Distributes requests evenly across available providers. Good for load balancing.

### Priority
Uses a primary provider and falls back to others only when the primary is unavailable or over-loaded.

### Custom
Define your own routing rules based on model, user, token count, or custom metadata.

## Failover

If a provider returns an error (5xx, timeout, rate limit), the gateway automatically retries with the next available provider. This happens transparently — your application sees a successful response.

**Failover chain example:**
```
OpenAI (primary) → Azure OpenAI (secondary) → AWS Bedrock (tertiary)
```

Configurable per model or globally.

## Cross-Region Inference

Route requests to providers in specific regions for:
- **Data residency**: Keep requests in EU, US, or other regions
- **Latency**: Route to the nearest region
- **Compliance**: Meet regulatory requirements

Example: Route European users to Azure OpenAI (West Europe) and US users to OpenAI (US).

## Model Aliases

Create custom model names that map to specific provider models:

| Alias | Resolves To |
|-------|-------------|
| `fast` | `groq/llama-3.1-70b` |
| `smart` | `openai/gpt-4o` |
| `cheap` | `anthropic/claude-3-haiku` |
| `default` | `anthropic/claude-sonnet-4-20250514` |

Use aliases in your code:
```json
{
  "model": "fast",
  "messages": [{"role": "user", "content": "Hello"}]
}
```

The gateway resolves the alias and routes to the correct provider.

## Rate Limiting

The gateway handles rate limiting at two levels:
1. **Provider-level**: Respects each provider's rate limits, queues or reroutes when hit
2. **Key-level**: Set custom rate limits per gateway API key

## Usage Tracking

All requests through the gateway are logged with:
- Model used
- Provider that served the request
- Token counts (prompt + completion)
- Latency
- Cost estimate

Query logs with the `get_gateway_logs` tool. Get aggregated stats with `gateway_usage`.
