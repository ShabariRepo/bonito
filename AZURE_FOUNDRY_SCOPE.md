# Azure AI Foundry Integration — Scope Document

**Date:** 2026-02-15  
**Status:** Proposed  
**Priority:** High — fixes Azure gap without fighting Microsoft's quota system

---

## Problem

Azure OpenAI requires:
1. Explicit deployments per model (TPM allocation)
2. Quota approval per model per subscription — many subs have **0 TPM** by default
3. Only OpenAI models (no Llama, Mistral, DeepSeek, etc.)

This makes Azure the worst onboarding experience of our 3 providers. AWS Bedrock and GCP Vertex "just work" after credentials.

## Solution

Support **Azure AI Foundry** (Microsoft's new unified platform) as the default Azure option, while keeping Azure OpenAI as a legacy option for existing users.

### What Foundry Gives Us

| Feature | Azure OpenAI (current) | Azure AI Foundry (new) |
|---|---|---|
| Resource type | `kind: OpenAI` | `kind: AIServices` |
| Models | OpenAI only | OpenAI + DeepSeek + Llama + Mistral + xAI + Cohere |
| Endpoint | `https://<r>.openai.azure.com/openai/deployments/{name}/...` | `https://<r>.services.ai.azure.com/models/chat/completions` |
| Routing | Per-deployment URLs | Single endpoint, `model` parameter |
| Deployment SKU | `Standard` (regional, low quota) | `GlobalStandard` (global, highest quota) |
| Partner models | ❌ | ✅ Marketplace, pay-per-token |
| LiteLLM prefix | `azure/{deployment_name}` | `azure_ai/{deployment_name}` |
| Auth | API key or Azure AD | API key or Microsoft Entra ID |

### Key Insight

Even in Foundry, deployments are still required. **But:**
- `GlobalStandard` SKU has the highest default quota across Azure
- Partner models (DeepSeek, Llama, Mistral) use Marketplace subscriptions — different quota system entirely
- Single inference endpoint simplifies our gateway (no per-deployment URL routing)
- Microsoft is actively pushing everyone toward Foundry — this is where investment goes

---

## Architecture

### User Flow (New Azure Setup)

```
Connect Azure → "Which Azure service?" → [Azure AI Foundry (recommended)] / [Azure OpenAI (legacy)]
                                                    ↓
                                        Enter: API Key + Resource Endpoint
                                        (or Service Principal for management)
                                                    ↓
                                        Bonito lists available models
                                                    ↓
                                        User activates models → Bonito auto-deploys (GlobalStandard)
                                                    ↓
                                        Gateway routes via azure_ai/ prefix
```

### Credential Requirements

**Azure AI Foundry (simple — API key mode):**
- API Key (`az cognitiveservices account keys list`)
- Resource endpoint: `https://<resource>.services.ai.azure.com`
- That's it. Customer never touches Azure Portal again.

**Azure AI Foundry (full — service principal mode, for auto-deploy):**
- All of the above, plus:
- Tenant ID, Client ID, Client Secret (for ARM API deployment management)
- Subscription ID, Resource Group

**Azure OpenAI (legacy — unchanged):**
- Same as today: endpoint + service principal creds

### Data Model

```python
# CloudProvider.config or Vault secret gets a new field:
{
    "azure_mode": "foundry" | "openai",     # NEW — default "foundry"
    "endpoint": "https://...",               # Foundry: .services.ai.azure.com
    "api_key": "...",                        # Foundry: cognitive services key
    "tenant_id": "...",                      # Optional: for ARM management
    "client_id": "...",
    "client_secret": "...",
    "subscription_id": "...",
    "resource_group": "..."
}
```

---

## Implementation Plan

### Phase 1: Backend — Dual-Mode Provider (2-3 days)

**File: `backend/app/services/providers/azure_foundry.py`**

1. Add `azure_mode` parameter to `AzureFoundryProvider.__init__`
2. **Model listing (Foundry mode):**
   - Use existing ARM API: `az cognitiveservices account list-models`
   - Parse available SKUs from model response (GlobalStandard, Standard, etc.)
   - Show all models: OpenAI + Partner models
3. **Model invocation (Foundry mode):**
   - New endpoint: `POST https://<resource>.services.ai.azure.com/models/chat/completions`
   - Auth: `api-key` header (not `Authorization: Bearer`)
   - Body includes `model` field (deployment name)
4. **Deployment creation (Foundry mode):**
   - Same ARM API (`Microsoft.CognitiveServices/accounts/deployments`)
   - Default SKU: `GlobalStandard`
   - For partner models: handle Marketplace subscription flow
5. **Keep Azure OpenAI mode unchanged** — all existing code paths preserved

**File: `backend/app/services/gateway.py`**

6. In `_build_model_list`:
   - Read `azure_mode` from provider credentials
   - Foundry mode: use `azure_ai/{deployment_name}` prefix + `api_key` + `api_base`
   - OpenAI mode: use `azure/{deployment_name}` prefix (unchanged)

**File: `backend/app/schemas/provider.py` / `onboarding.py`**

7. Add `azure_mode` field to Azure credential schemas
8. Simplify Foundry onboarding: only require `api_key` + `endpoint` (no service principal needed for basic usage)

### Phase 2: Frontend — Azure Type Selector (1-2 days)

9. Azure onboarding step: radio/toggle for "Azure AI Foundry" (default) vs "Azure OpenAI"
10. Foundry credential form: API Key + Endpoint URL (2 fields vs 6 for legacy)
11. Model catalog page: show Foundry-specific models with partner badges
12. Deployment creation: show `GlobalStandard` as default SKU

### Phase 3: Testing & Polish (1 day)

13. Create an `AIServices` resource for testing (or upgrade existing)
14. Deploy a model via GlobalStandard → verify gateway call works
15. Test partner model (e.g., DeepSeek) via Marketplace
16. Verify Azure OpenAI legacy mode still works (regression)
17. Update pricing table for non-OpenAI models

---

## What We're NOT Building (Yet)

- **Marketplace subscription automation** — Partner models require Azure Marketplace agreement. V1 will guide users to accept terms manually. V2 can automate via ARM API.
- **Entra ID keyless auth** — Nice to have, but API key works fine for V1.
- **Resource creation** — We won't auto-create Foundry resources. Customer brings their own.
- **Data zone selection** — V1 uses GlobalStandard everywhere. Compliance-conscious customers can configure DataZone later.

---

## Risk Assessment

| Risk | Impact | Mitigation |
|---|---|---|
| GlobalStandard quota still 0 for some subs | High | Partner models bypass this; guide users to request quota |
| LiteLLM `azure_ai/` prefix bugs | Medium | LiteLLM actively supports this; we can pin version |
| Existing Azure OpenAI users broken | High | Dual-mode: legacy preserved, no code paths touched |
| Partner models need Marketplace terms | Low | V1: manual acceptance, V2: automate |

---

## Effort Summary

| Task | Estimate | Depends On |
|---|---|---|
| Backend dual-mode provider | 2 days | — |
| Gateway LiteLLM integration | 0.5 day | Backend |
| Frontend Azure type selector | 1 day | Backend API |
| Frontend credential form | 0.5 day | Backend API |
| Testing (with real Foundry resource) | 1 day | All above |
| **Total** | **~5 days** | |

---

## Immediate Next Steps

1. **Create an AIServices resource** to test against (or check if existing resource can be upgraded)
2. Check GlobalStandard quota on AIServices resource — it might be different from OpenAI resource
3. Implement backend dual-mode support
4. Test with LiteLLM `azure_ai/` prefix

---

## References

- [Foundry Models Endpoints](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/endpoints)
- [Deployment Types](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/deployment-types)
- [Create Deployments (CLI/Bicep)](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/how-to/create-model-deployments)
- [Models Sold by Azure](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/models-sold-directly-by-azure)
- [LiteLLM Azure AI](https://docs.litellm.ai/docs/providers/azure_ai)
- [LiteLLM Azure OpenAI](https://docs.litellm.ai/docs/providers/azure)
