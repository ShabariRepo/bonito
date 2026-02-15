# Bonito — Chatbot Knowledge Base

> This document is the source of truth for the Bonito website chatbot. It covers onboarding, provider setup, common issues, and feature overviews so the bot can help users get started quickly.

---

## 1. Getting Started

### What is Bonito?

Bonito is a unified AI gateway that lets you connect your own cloud AI providers (AWS Bedrock, Azure OpenAI, and Google Cloud Vertex AI) and manage all your models from a single dashboard. Instead of juggling multiple consoles and API keys, you connect your cloud accounts to Bonito and get:

- A **single API endpoint** compatible with the OpenAI Chat Completions format
- A **Playground** to test and compare models side by side
- **Routing Policies** to automatically pick the best model based on cost, latency, or capability
- **Cost Tracking** and **Compliance** controls across all providers
- **One-click Model Activation** to enable new models without leaving Bonito

### How to Connect a Provider

1. Log in to Bonito and go to the **Providers** page.
2. Click **Add Provider** and choose AWS, Azure, or GCP.
3. Enter the required credentials (see Provider Setup below).
4. Click **Connect**. Bonito will validate your credentials and list all available models.
5. Enable the models you want to use (see Model Activation below).

---

## 2. Provider Setup

### Amazon Web Services (AWS Bedrock)

**Required credentials:**

| Field | Description |
|---|---|
| **Access Key ID** | Your AWS IAM access key |
| **Secret Access Key** | Your AWS IAM secret key |

**Permissions needed:**

Bonito offers two IAM setup modes:

**Quick Start** — Single broad policy (good for evaluation):
- Attach the Bonito managed policy with all Bedrock + Cost Explorer permissions.

**Enterprise (recommended for production)** — Separate least-privilege policies per capability:

| Policy | Actions | Required? |
|--------|---------|-----------|
| **Core** | `bedrock:ListFoundationModels`, `GetFoundationModel`, `InvokeModel`, `InvokeModelWithResponseStream`, `sts:GetCallerIdentity` | ✅ Always |
| **Provisioning** | `bedrock:Create/Get/Update/Delete/ListProvisionedModelThroughput` | Only if deploying reserved capacity |
| **Model Activation** | `bedrock:PutFoundationModelEntitlement` | Only if enabling models from Bonito UI |
| **Cost Tracking** | `ce:GetCostAndUsage`, `GetCostForecast`, `GetDimensionValues`, `GetTags` | Only if you want spend visibility |

**Minimum to get started:** Core policy only (5 Bedrock actions + STS).

Example IAM policy (core only):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel",
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["sts:GetCallerIdentity"],
      "Resource": "*"
    }
  ]
}
```

> **Tip:** Bonito's IaC templates (Terraform) include both modes — set `iam_mode = "least_privilege"` for enterprise or `"managed"` for quick start.

---

### Microsoft Azure (Azure OpenAI)

**Required credentials:**

| Field | Description |
|---|---|
| **Tenant ID** | Your Azure Active Directory tenant ID |
| **Client ID** | The Application (client) ID of your service principal |
| **Client Secret** | The service principal's secret value |
| **Subscription ID** | Your Azure subscription ID |
| **Resource Group** | The resource group containing your Azure OpenAI resource |
| **Endpoint URL** | Your Azure OpenAI resource endpoint |

**Important — Endpoint URL:**

The endpoint **must** be an Azure OpenAI resource endpoint with a custom subdomain. It looks like this:

```
https://your-resource-name.openai.azure.com/
```

A generic regional endpoint like `https://eastus.api.cognitive.microsoft.com/` will **not** work for model listing. You need to create an Azure OpenAI resource with a custom subdomain in the Azure portal first, then use that endpoint.

**Permissions needed:**

Bonito offers two RBAC setup modes:

**Quick Start** — Assign `Cognitive Services Contributor` on the Azure OpenAI resource. This is a broad managed role — quick to set up but grants more access than strictly needed.

**Enterprise (recommended for production)** — Create a custom role with only the exact permissions Bonito uses:

| Category | Actions | Why |
|----------|---------|-----|
| **Account** | `Microsoft.CognitiveServices/accounts/read` | Validate connection |
| **Deployments** | `accounts/deployments/read`, `write`, `delete` | Create, scale, delete model deployments |
| **Models** | `accounts/models/read` | List available models |
| **Inference** | `accounts/OpenAI/deployments/chat/completions/action`, `completions/action`, `embeddings/action` | Call models |

Plus `Cost Management Reader` at subscription scope for spend visibility (optional).

Example custom role (Azure CLI):
```bash
az role definition create --role-definition '{
  "Name": "Bonito AI Operator",
  "Actions": [
    "Microsoft.CognitiveServices/accounts/read",
    "Microsoft.CognitiveServices/accounts/deployments/read",
    "Microsoft.CognitiveServices/accounts/deployments/write",
    "Microsoft.CognitiveServices/accounts/deployments/delete",
    "Microsoft.CognitiveServices/accounts/models/read"
  ],
  "DataActions": [
    "Microsoft.CognitiveServices/accounts/OpenAI/deployments/chat/completions/action",
    "Microsoft.CognitiveServices/accounts/OpenAI/deployments/completions/action",
    "Microsoft.CognitiveServices/accounts/OpenAI/deployments/embeddings/action"
  ],
  "AssignableScopes": ["/subscriptions/YOUR_SUBSCRIPTION_ID"]
}'
```

> **Tip:** Bonito's IaC templates (Terraform) include both modes — set `rbac_mode = "least_privilege"` for enterprise or `"managed"` for quick start.

---

### Google Cloud Platform (GCP — Vertex AI)

**Required credentials:**

| Field | Description |
|---|---|
| **Project ID** | Your GCP project ID |
| **Service Account JSON** | The full JSON key file for your service account |

**How to enter the Service Account JSON:**

Paste the **entire contents** of your service account JSON key file into the field. It should look like this:

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n",
  "client_email": "...",
  "client_id": "...",
  ...
}
```

Bonito validates the JSON on the frontend before sending, so you'll get an immediate error if the format is wrong.

**Permissions needed:**

Bonito offers two IAM setup modes:

**Quick Start** — Assign `roles/aiplatform.user` to the service account. This is already fairly scoped — fine for most use cases.

**Enterprise (recommended for production)** — Create a custom role with only the exact permissions:

| Category | Permissions | Why |
|----------|------------|-----|
| **Discovery** | `aiplatform.publishers.get`, `publisherModels.get` | List available models |
| **Invocation** | `aiplatform.endpoints.predict` | Call models |
| **Endpoints** | `aiplatform.endpoints.create/get/list/update/delete/deploy/undeploy` | Manage dedicated endpoints |
| **Models** | `aiplatform.models.list`, `get` | Model metadata |
| **Validation** | `resourcemanager.projects.get` | Verify project access |

Plus `roles/billing.viewer` on billing account for spend visibility (optional).

> **Tip:** Bonito's IaC templates (Terraform) include both modes — set `iam_mode = "least_privilege"` for enterprise or `"managed"` for quick start.

---

## 3. Common Issues & Fixes

### "Connected! Found 0 models"

This usually means the credentials connected successfully, but model listing failed silently.

- **Azure:** Make sure your Endpoint URL is an Azure OpenAI resource endpoint (e.g., `https://your-resource-name.openai.azure.com/`), not a generic regional endpoint. Also check that the resource group is correct.
- **GCP:** Ensure the Vertex AI API is enabled in your GCP project.
- **AWS:** Verify your IAM user has Bedrock permissions and you're in a region where Bedrock is available.

### GCP JSON Parsing Errors

If you get an error when pasting your GCP service account JSON:

- Make sure you're pasting the **raw JSON** content, not a file path or a screenshot.
- The JSON must be valid — Bonito validates it in the browser before sending.
- If you copied from a terminal or text editor, make sure no extra characters were added.

### Rate Limit Errors

If you see a rate limit or "too many requests" error:

- Wait 30–60 seconds and try again.
- This can happen if you're making many changes quickly (updating credentials, refreshing model lists, etc.).

### 502 or Timeout Errors

If you see a 502 error or the request times out:

- Try refreshing the page and retrying after a moment.
- If the issue persists, the backend service may need a restart — contact support.

### Models Showing a 🔒 Lock Icon

A lock icon means the model exists in your provider's catalog but is **not yet enabled** in your cloud account. To use it:

1. Click the **Enable** button on the model card in Bonito, or
2. Enable the model directly in your cloud provider's console:
   - **AWS:** Go to the Bedrock console → Model Access → Request access
   - **Azure:** Create a deployment for the model in your Azure OpenAI resource
   - **GCP:** Ensure the Vertex AI API is enabled and the model is available in your region

Bonito also supports **bulk activation** — select multiple models and enable them all at once.

### Playground Returns a 500 Error

This can happen if:

- **The model is not a chat model.** Embedding models (like `text-embedding-ada-002`), older completion models (like `babbage`), or specialized models (like BERT) can't be used in the Playground. Bonito filters these out automatically, but if you see this error, double-check the model type.
- **The model isn't enabled in your account.** Check if the model shows a 🔒 icon on the Models page and enable it first.
- **The model isn't available in your region.** Some models are region-restricted. Check your provider's documentation.

---

## 4. Features

### Playground

Test any connected model directly in Bonito. Features include:

- **Single model chat** — pick a model and start chatting
- **Compare mode** — run the same prompt against two models side by side
- **Searchable model picker** — filter by provider (AWS / Azure / GCP) and search by name
- Only chat-capable, enabled models appear in the picker

### Routing Policies

Set up rules to automatically route requests to the best model based on:

- **Cost** — prefer cheaper models
- **Latency** — prefer faster models
- **Capability** — match model strengths to request types
- **Fallback chains** — if one model fails, automatically try another

### Gateway API Keys

Generate API keys to access your models through Bonito's unified gateway endpoint. One key, all your providers.

### Model Activation

Enable models directly from the Bonito dashboard:

- **One-click enable** — activate individual models with a single click
- **Bulk enable** — select up to 20 models and enable them all at once
- Bonito handles the provider-specific activation (Bedrock entitlements, Azure deployments, GCP API enablement)
- Some models may require approval from the provider and won't activate instantly

### Deployment Provisioning

Deploy AI models directly into your cloud from the Bonito UI — no console-hopping required.

**How it works per provider:**

| Provider | Deployment Type | What Bonito Creates |
|----------|----------------|-------------------|
| **AWS Bedrock** | On-demand (free) or Provisioned Throughput (reserved capacity) | On-demand: validates access. PT: creates real reserved capacity with commitment (1 week–6 months) |
| **Azure OpenAI** | Model deployment with TPM capacity | Creates a real deployment on your Azure OpenAI resource via ARM API (Standard or GlobalStandard tier) |
| **GCP Vertex AI** | Serverless (no provisioning needed) | Verifies access — GCP models are serverless by default |

**AWS Provisioned Throughput notes:**
- Minimum commitment: 1 month (for model unit-based PT)
- Not all models support PT — only specific context-window variants (e.g., `nova-micro-v1:0:128k`)
- Costs real money ($20+/hr per model unit) — use on-demand for testing
- Requires `bedrock:CreateProvisionedModelThroughput` IAM permission

**Azure deployment notes:**
- Requires TPM quota for the model in your subscription
- If you get a quota error, request increase in Azure Portal → Quotas
- Requires `Cognitive Services Contributor` or the Bonito custom role

### Cost Tracking

Monitor spend across all connected providers from a single dashboard. See costs broken down by model, provider, and time period.

### Compliance

Set organizational policies for model usage, including which models are approved, spending limits, and access controls.

---

## 5. Updating Credentials

You can update your provider credentials at any time without re-entering everything:

1. Go to the **Providers** page and click on the provider you want to update.
2. Only fill in the fields you want to change — leave the rest blank.
3. Blank fields keep their current values (you'll see "Keep current" placeholders).
4. Click **Save** to apply the changes.

This is useful when you need to rotate a secret key or update an endpoint without re-entering your tenant ID, project ID, etc.

---

## 6. Using the Gateway API

Bonito provides an OpenAI-compatible API endpoint so you can use any connected model with tools that support the OpenAI format (LangChain, LlamaIndex, custom apps, etc.).

### Endpoint

```
POST https://gateway.getbonito.com/v1/chat/completions
```

### Authentication

Include your Bonito Gateway API key in the `Authorization` header:

```
Authorization: Bearer YOUR_BONITO_API_KEY
```

You can generate API keys from the **Gateway** page in the Bonito dashboard.

### Example Request

```bash
curl https://gateway.getbonito.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_BONITO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "anthropic.claude-3-sonnet-20240229-v1:0",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "max_tokens": 256
  }'
```

### Using with Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://gateway.getbonito.com/v1",
    api_key="YOUR_BONITO_API_KEY"
)

response = client.chat.completions.create(
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

### Model Names

Use the model identifiers shown on the **Models** page in Bonito. These are the provider-native model IDs (e.g., `anthropic.claude-3-sonnet-20240229-v1:0` for AWS Bedrock, `gpt-4o` for Azure, `gemini-1.5-pro` for GCP).

---

## 7. Getting Help

If you're stuck or something isn't working as expected:

- Check the [Common Issues & Fixes](#3-common-issues--fixes) section above
- Contact support at **support@getbonito.com**
- Visit our documentation at **docs.getbonito.com**
