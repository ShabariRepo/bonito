# /bonito:cost-report

Get a cost breakdown across all connected providers.

## Usage

```
/bonito:cost-report [--period 24h|7d|30d]
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--period` | No | `30d` | Time period for the report |

## What it does

1. Lists all connected providers
2. Fetches cost data for each provider over the specified period
3. Fetches gateway usage statistics
4. Presents a summary table with:
   - Cost per provider
   - Total requests per provider
   - Most-used models
   - Total spend across all providers

## Example Output

```
Provider          Requests    Cost
─────────────────────────────────────
OpenAI            12,450      $34.20
Anthropic          8,200      $28.50
AWS Bedrock        3,100      $12.80
─────────────────────────────────────
Total             23,750      $75.50
```

## Notes

- Costs are approximate and based on token usage tracked by the gateway
- For exact billing, check each provider's dashboard directly
