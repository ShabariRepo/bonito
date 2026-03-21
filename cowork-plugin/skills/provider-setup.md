# Provider Setup

How to connect each AI provider to Bonito.

## General Flow

1. **Get credentials** from the provider's console
2. **Connect** via the Bonito dashboard or API (`connect_provider` tool)
3. **Verify** the connection (`verify_provider` tool)
4. **Sync models** to discover available models (`sync_models` tool)
5. **Activate** the models you want to use (`activate_model` tool)

## Provider-Specific Setup

### OpenAI
```json
{
  "provider_type": "openai",
  "credentials": {
    "api_key": "$OPENAI_API_KEY"
  }
}
```
- Get your API key from: https://platform.openai.com/api-keys

### Anthropic
```json
{
  "provider_type": "anthropic",
  "credentials": {
    "api_key": "$ANTHROPIC_API_KEY"
  }
}
```
- Get your API key from: https://console.anthropic.com/settings/keys

### AWS Bedrock
```json
{
  "provider_type": "aws_bedrock",
  "credentials": {
    "access_key_id": "$AWS_ACCESS_KEY_ID",
    "secret_access_key": "$AWS_SECRET_ACCESS_KEY",
    "region": "us-east-1"
  }
}
```
- Requires IAM credentials with Bedrock permissions
- Enable model access in the AWS Bedrock console first

### Azure OpenAI
```json
{
  "provider_type": "azure_openai",
  "credentials": {
    "api_key": "$AZURE_OPENAI_API_KEY",
    "endpoint": "https://your-resource.openai.azure.com",
    "api_version": "2024-02-01"
  }
}
```
- Deploy models in Azure OpenAI Studio first
- The endpoint is your Azure resource URL

### GCP Vertex AI
```json
{
  "provider_type": "gcp_vertex",
  "credentials": {
    "project_id": "your-gcp-project",
    "location": "us-central1",
    "service_account_key": "$GCP_SERVICE_ACCOUNT_JSON"
  }
}
```
- Requires a service account with Vertex AI permissions
- Enable the Vertex AI API in your GCP project

### Groq
```json
{
  "provider_type": "groq",
  "credentials": {
    "api_key": "$GROQ_API_KEY"
  }
}
```
- Get your API key from: https://console.groq.com/keys
- Known for ultra-fast inference on Llama and Mixtral models

## Verifying a Connection

After connecting, verify the provider is reachable:

```
verify_provider(provider_id="<id-from-connect-response>")
```

A successful verification confirms credentials are valid and the provider's API is accessible.

## Tips

- You can connect **multiple instances** of the same provider type (e.g., two AWS regions)
- Credentials are encrypted at rest and never exposed in API responses
- If verification fails, double-check that the credentials have the required permissions
