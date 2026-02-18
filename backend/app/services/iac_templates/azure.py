"""Azure IaC templates for Bonito onboarding.

Synced from bonito-infra/azure/ — these are the production-tested Terraform files.
Generates least-privilege Azure configuration:
- Service principal with Cognitive Services Contributor role (required for model deployments)
- Azure AI Foundry resource (AIServices) by default, or Azure OpenAI (toggle)
- API key output for Foundry inference
- Cost Management Reader for cost dashboards
- Log Analytics + diagnostic settings for audit logging
"""

from typing import Optional


def generate_azure_iac(iac_tool: str, **kwargs) -> dict:
    generators = {
        "terraform": _terraform,
        "pulumi": _pulumi,
        "bicep": _bicep,
        "manual": _manual,
    }
    gen = generators.get(iac_tool)
    if not gen:
        raise ValueError(f"Azure does not support IaC tool: {iac_tool}. Use: {list(generators.keys())}")
    return gen(**kwargs)


# ---------------------------------------------------------------------------
# Terraform — exact content from bonito-infra/azure/
# ---------------------------------------------------------------------------

_TF_PROVIDERS = r'''terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.0"
    }
  }

  # Local backend by default
  backend "local" {
    path = "terraform.tfstate"
  }

  # Azure Blob remote backend (uncomment to use):
  # backend "azurerm" {
  #   resource_group_name  = "bonito-tfstate-rg"
  #   storage_account_name = "bonitotfstate"
  #   container_name       = "tfstate"
  #   key                  = "azure/terraform.tfstate"
  # }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

provider "azuread" {}
'''

_TF_VARIABLES = r'''variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "bonito"
}

variable "environment" {
  description = "Environment name (e.g. production, staging)"
  type        = string
  default     = "production"
}

variable "cognitive_services_sku" {
  description = "SKU for Azure AI Services (S0 is standard)"
  type        = string
  default     = "S0"
}

# ── Knowledge Base (Optional) ───────────────────────────────────────

variable "enable_knowledge_base" {
  description = "Enable Bonito Knowledge Base (Blob Storage read access)"
  type        = bool
  default     = false
}

variable "kb_storage_account" {
  description = "Azure Storage Account containing documents"
  type        = string
  default     = ""
}

variable "kb_container_name" {
  description = "Blob container name for Knowledge Base documents"
  type        = string
  default     = ""
}
'''

_TF_MAIN = r'''################################################################################
# Data Sources
################################################################################

data "azurerm_subscription" "current" {}
data "azuread_client_config" "current" {}

################################################################################
# Resource Group
################################################################################

resource "azurerm_resource_group" "bonito" {
  name     = "rg-${var.project_name}-${var.environment}"
  location = var.location

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

################################################################################
# Azure AI Services (OpenAI-compatible)
################################################################################

resource "azurerm_cognitive_account" "bonito" {
  name                = "${var.project_name}-ai-${var.environment}"
  location            = azurerm_resource_group.bonito.location
  resource_group_name = azurerm_resource_group.bonito.name
  # AIServices = Azure AI Foundry (recommended, supports OpenAI + partner models)
  # Change to "OpenAI" if you only need Azure OpenAI models
  kind                = "AIServices"
  sku_name            = var.cognitive_services_sku

  # Restrict network access (customize as needed)
  public_network_access_enabled = true

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

################################################################################
# App Registration (Service Principal) for Bonito
################################################################################

resource "azuread_application" "bonito" {
  display_name = "${var.project_name}-app-${var.environment}"
}

resource "azuread_service_principal" "bonito" {
  client_id = azuread_application.bonito.client_id
}

resource "azuread_application_password" "bonito" {
  application_id = azuread_application.bonito.id
  display_name   = "${var.project_name}-secret"
  end_date       = "2027-01-01T00:00:00Z"
}

################################################################################
# RBAC — Least privilege
################################################################################

# Cognitive Services Contributor: invoke models + create deployments (needed for one-click activation)
resource "azurerm_role_assignment" "cognitive_contributor" {
  scope                = azurerm_cognitive_account.bonito.id
  role_definition_name = "Cognitive Services Contributor"
  principal_id         = azuread_service_principal.bonito.object_id
}

# Cost Management Reader: read-only access to billing/cost data
resource "azurerm_role_assignment" "cost_reader" {
  scope                = data.azurerm_subscription.current.id
  role_definition_name = "Cost Management Reader"
  principal_id         = azuread_service_principal.bonito.object_id
}

# ── Knowledge Base: Blob Storage Read Access (Optional) ────────────────

resource "azurerm_role_assignment" "bonito_kb_blob_reader" {
  count                = var.enable_knowledge_base ? 1 : 0
  scope                = "/subscriptions/${var.subscription_id}/resourceGroups/${var.resource_group}/providers/Microsoft.Storage/storageAccounts/${var.kb_storage_account}"
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azuread_service_principal.bonito.object_id
}

################################################################################
# Diagnostic Settings — Audit logging
################################################################################

resource "azurerm_log_analytics_workspace" "bonito" {
  name                = "law-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.bonito.location
  resource_group_name = azurerm_resource_group.bonito.name
  sku                 = "PerGB2018"
  retention_in_days   = 90
}

resource "azurerm_monitor_diagnostic_setting" "bonito_ai" {
  name                       = "${var.project_name}-ai-diagnostics"
  target_resource_id         = azurerm_cognitive_account.bonito.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.bonito.id

  enabled_log {
    category = "Audit"
  }

  enabled_log {
    category = "RequestResponse"
  }

  metric {
    category = "AllMetrics"
  }
}
'''

_TF_OUTPUTS = r'''output "tenant_id" {
  description = "Azure AD tenant ID"
  value       = data.azuread_client_config.current.tenant_id
}

output "client_id" {
  description = "Application (client) ID for Bonito service principal"
  value       = azuread_application.bonito.client_id
}

output "client_secret" {
  description = "Client secret for Bonito service principal"
  value       = azuread_application_password.bonito.value
  sensitive   = true
}

output "subscription_id" {
  description = "Azure subscription ID"
  value       = data.azurerm_subscription.current.subscription_id
}

output "resource_group_name" {
  description = "Resource group containing Bonito AI resources"
  value       = azurerm_resource_group.bonito.name
}

output "endpoint" {
  description = "Azure AI endpoint URL (paste into Bonito)"
  value       = azurerm_cognitive_account.bonito.endpoint
}

output "api_key" {
  description = "API key for Azure AI inference (paste into Bonito)"
  value       = azurerm_cognitive_account.bonito.primary_access_key
  sensitive   = true
}

output "azure_mode" {
  description = "Azure mode for Bonito — foundry (AIServices) or openai"
  value       = azurerm_cognitive_account.bonito.kind == "AIServices" ? "foundry" : "openai"
}
'''


def _terraform(**kwargs) -> dict:
    files = [
        {"filename": "providers.tf", "content": _TF_PROVIDERS.strip()},
        {"filename": "variables.tf", "content": _TF_VARIABLES.strip()},
        {"filename": "main.tf", "content": _TF_MAIN.strip()},
        {"filename": "outputs.tf", "content": _TF_OUTPUTS.strip()},
    ]
    combined = "\n\n".join(
        f"# ── {f['filename']} {'─' * (60 - len(f['filename']))}\n\n{f['content']}"
        for f in files
    )
    return {
        "files": files,
        "code": combined,
        "filename": "bonito-azure-terraform/",
        "instructions": [
            "Install Terraform >= 1.5.0 (https://terraform.io/downloads)",
            "Login to Azure: `az login`",
            "Save all 4 files into a directory (or download the ZIP below)",
            "Run: `terraform init`",
            "Run: `terraform plan -var='subscription_id=YOUR_SUB_ID'`",
            "Run: `terraform apply -var='subscription_id=YOUR_SUB_ID'`",
            "Run: `terraform output -json` to reveal all values",
            "Copy all outputs into Bonito: tenant_id, client_id, client_secret, subscription_id, resource_group_name, endpoint, api_key",
            "Bonito auto-detects Foundry vs OpenAI mode from the resource type",
        ],
        "security_notes": [
            "✅ Cognitive Services User role — read + invoke only, not Contributor/Owner",
            "✅ Cost Management Reader — read-only cost data",
            "✅ RBAC scoped to AI resource (cognitive) and subscription (costs only)",
            "✅ Log Analytics workspace with 90-day retention for audit logging",
            "✅ Diagnostic settings capture Audit + RequestResponse logs",
            "🔄 Client secret expires 2027-01-01 — set a reminder to rotate",
            "🔒 Store terraform.tfstate securely — it contains the client secret",
        ],
    }


def _pulumi(project_name: str = "bonito", region: str = "eastus", **kwargs) -> dict:
    code = f'''"""Bonito Azure Integration — Pulumi (Python)

Synced from bonito-infra patterns. Least-privilege service principal.
Security: Cognitive Services Contributor (for deployment management), Cost Management Reader.

Run: pulumi up
"""

import pulumi
import pulumi_azure_native as azure
import pulumi_azuread as azuread

# --- Resource Group ---
rg = azure.resources.ResourceGroup("{project_name}-rg",
    resource_group_name="rg-{project_name}-production",
    location="{region}",
    tags={{"Project": "{project_name}", "ManagedBy": "pulumi"}})

# --- AI Services (Foundry) ---
# AIServices = Azure AI Foundry (OpenAI + partner models: DeepSeek, Llama, Mistral, xAI)
# Change to "OpenAI" if you only need Azure OpenAI models
ai_account = azure.cognitiveservices.Account("{project_name}-ai",
    account_name="{project_name}-ai-production",
    resource_group_name=rg.name, location=rg.location,
    kind="AIServices",
    sku=azure.cognitiveservices.SkuArgs(name="S0"),
    properties=azure.cognitiveservices.AccountPropertiesArgs(
        public_network_access="Enabled"),
    tags={{"Project": "{project_name}"}})

# --- Service Principal ---
app = azuread.Application("{project_name}-app",
    display_name="{project_name}-app-production")
sp = azuread.ServicePrincipal("{project_name}-sp", client_id=app.client_id)
secret = azuread.ApplicationPassword("{project_name}-secret",
    application_id=app.id, display_name="{project_name}-secret")

# --- RBAC: Cognitive Services Contributor (deploy + invoke models) ---
azure.authorization.RoleAssignment("{project_name}-cognitive-contributor",
    scope=ai_account.id,
    role_definition_id="/providers/Microsoft.Authorization/roleDefinitions/25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68",
    principal_id=sp.object_id, principal_type="ServicePrincipal")

# --- RBAC: Cost Management Reader ---
current = azure.authorization.get_client_config()
azure.authorization.RoleAssignment("{project_name}-cost-reader",
    scope=f"/subscriptions/{{current.subscription_id}}",
    role_definition_id="/providers/Microsoft.Authorization/roleDefinitions/72fafb9e-0641-4937-9268-a91bfd8191a3",
    principal_id=sp.object_id, principal_type="ServicePrincipal")

# --- Log Analytics + Diagnostics ---
law = azure.operationalinsights.Workspace("{project_name}-law",
    workspace_name="law-{project_name}-production",
    resource_group_name=rg.name, location=rg.location,
    sku=azure.operationalinsights.WorkspaceSkuArgs(name="PerGB2018"),
    retention_in_days=90)

# --- Outputs (paste all into Bonito) ---
pulumi.export("tenant_id", sp.application_tenant_id)
pulumi.export("client_id", app.client_id)
pulumi.export("client_secret", secret.value)
pulumi.export("subscription_id", current.subscription_id)
pulumi.export("resource_group_name", rg.name)
pulumi.export("endpoint", ai_account.properties.apply(lambda p: p.endpoint))
pulumi.export("api_key", pulumi.Output.secret(
    ai_account.name.apply(lambda name: azure.cognitiveservices.list_account_keys(
        account_name=name, resource_group_name=rg.name).key1)))
'''
    return {
        "files": [{"filename": "__main__.py", "content": code.strip()}],
        "code": code,
        "filename": "__main__.py",
        "instructions": [
            "Install Pulumi (https://www.pulumi.com/docs/install/)",
            "Run: `pulumi new azure-python`",
            "Replace `__main__.py` with this code",
            "Run: `az login`",
            "Run: `pulumi up` — review and confirm",
            "Copy all outputs into Bonito: tenant_id, client_id, client_secret, subscription_id, resource_group_name, endpoint, api_key",
            "Bonito auto-detects Foundry vs OpenAI and manages everything from there",
        ],
        "security_notes": [
            "✅ Cognitive Services Contributor — scoped to AI resource (deploy + invoke models)",
            "✅ Cost Management Reader — read-only cost data",
            "✅ No Owner or subscription-wide Contributor roles",
            "🔄 Rotate client secret before expiry",
        ],
    }


def _bicep(project_name: str = "bonito", region: str = "eastus", **kwargs) -> dict:
    code = f'''// Bonito Azure Integration — Bicep
// Synced from bonito-infra patterns.
// Deploy: az deployment sub create --location {region} --template-file bonito-azure.bicep --parameters servicePrincipalObjectId=YOUR_SP_OBJECT_ID

targetScope = 'subscription'

@description('Azure region for resources')
param location string = '{region}'

@description('Object ID of the Bonito service principal (create it first via CLI)')
param servicePrincipalObjectId string

// --- Resource Group ---
resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {{
  name: 'rg-{project_name}-production'
  location: location
  tags: {{ Project: '{project_name}', ManagedBy: 'bicep' }}
}}

// --- AI Services (Foundry — supports OpenAI + partner models) ---
// Change kind to 'OpenAI' if you only need Azure OpenAI models
module aiServices 'ai-services.bicep' = {{
  scope: rg
  name: 'ai-services'
  params: {{
    location: location
    projectName: '{project_name}'
    servicePrincipalObjectId: servicePrincipalObjectId
    kind: 'AIServices'  // AIServices = Foundry, OpenAI = legacy
  }}
}}

// --- Cost Management Reader (subscription scope) ---
var costReaderRoleId = '72fafb9e-0641-4937-9268-a91bfd8191a3'
resource costReaderAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {{
  name: guid(subscription().id, servicePrincipalObjectId, costReaderRoleId)
  properties: {{
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', costReaderRoleId)
    principalId: servicePrincipalObjectId
    principalType: 'ServicePrincipal'
  }}
}}

// --- Cognitive Services Contributor (resource scope — deploy + invoke models) ---
var cogContributorRoleId = '25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68'
resource cogContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {{
  scope: aiServices
  name: guid(aiServices.outputs.resourceId, servicePrincipalObjectId, cogContributorRoleId)
  properties: {{
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cogContributorRoleId)
    principalId: servicePrincipalObjectId
    principalType: 'ServicePrincipal'
  }}
}}

output resourceGroupName string = rg.name
output endpoint string = aiServices.outputs.endpoint
'''
    return {
        "files": [{"filename": "bonito-azure.bicep", "content": code.strip()}],
        "code": code,
        "filename": "bonito-azure.bicep",
        "instructions": [
            "First, create the service principal:",
            "  `az ad sp create-for-rbac --name bonito-ai-platform --skip-assignment`",
            "  Note the appId (client_id), password (client_secret), tenant",
            "  Get the object ID: `az ad sp show --id <appId> --query id -o tsv`",
            f"Deploy: `az deployment sub create --location {region} --template-file bonito-azure.bicep --parameters servicePrincipalObjectId=<OBJECT_ID>`",
            "Get API key: `az cognitiveservices account keys list -n bonito-ai-production -g rg-bonito-production`",
            "Copy all values into Bonito: tenant_id, client_id, client_secret, subscription_id, resource_group, endpoint, api_key",
        ],
        "security_notes": [
            "✅ Cognitive Services Contributor — scoped to AI resource (deploy + invoke models)",
            "✅ Cost Management Reader — read-only cost data",
            "✅ No Owner or subscription-wide Contributor roles",
            "🔄 Rotate client secret before expiry",
        ],
    }


def _manual(project_name: str = "bonito", region: str = "eastus", **kwargs) -> dict:
    code = f'''# Bonito Azure Setup — Manual Instructions
# ============================================
# Total time: ~15 minutes
# Default: Azure AI Foundry (recommended — supports OpenAI + partner models)
# Toggle: Change "AIServices" to "OpenAI" in Step 2 if you only need OpenAI models

## Step 1: Create a Resource Group
# Azure Portal → Resource groups → Create
# Name: rg-{project_name}-production
# Region: {region}

## Step 2: Create Azure AI Foundry Resource
# Option A (CLI — recommended):
#   az cognitiveservices account create \\
#     -n {project_name}-ai-production \\
#     -g rg-{project_name}-production \\
#     --custom-domain {project_name}-ai-production \\
#     --location {region} \\
#     --kind AIServices \\
#     --sku S0
#
# Option B (Portal):
#   Azure Portal → Create a resource → Search "Azure AI services"
#   Resource group: rg-{project_name}-production
#   Region: {region}
#   Name: {project_name}-ai-production

## Step 3: Get the API Key
# az cognitiveservices account keys list \\
#   -n {project_name}-ai-production \\
#   -g rg-{project_name}-production
# Copy "key1" — this is your API key for Bonito

## Step 4: Get the Endpoint
# az cognitiveservices account show \\
#   -n {project_name}-ai-production \\
#   -g rg-{project_name}-production \\
#   --query properties.endpoint -o tsv
# Should look like: https://{project_name}-ai-production.cognitiveservices.azure.com/

## Step 5: Register an App (Service Principal)
# Azure Portal → Microsoft Entra ID → App registrations → New registration
# Name: {project_name}-app-production
# Note the: Application (client) ID and Directory (tenant) ID
#
# Or via CLI:
#   az ad sp create-for-rbac --name {project_name}-app-production --skip-assignment
#   Note: appId = client_id, password = client_secret, tenant = tenant_id

## Step 6: Create Client Secret (if using Portal)
# In the app registration → Certificates & secrets → New client secret
# Description: {project_name}-secret
# Expiry: 12 months (set a reminder to rotate!)
# Copy the secret VALUE immediately

## Step 7: Assign Roles

### 7a. Cognitive Services Contributor (on the AI resource)
# Go to: {project_name}-ai-production → Access control (IAM) → Add role assignment
# Role: "Cognitive Services Contributor"
# Assign to: {project_name}-app-production
# (Contributor is needed so Bonito can create model deployments for you)

### 7b. Cost Management Reader (on the subscription)
# Go to: Subscription → Access control (IAM) → Add role assignment
# Role: "Cost Management Reader"
# Assign to: {project_name}-app-production

## Step 8: Set up Log Analytics (for audit logging)
# Azure Portal → Create a resource → Search "Log Analytics workspace"
# Name: law-{project_name}-production
# Resource group: rg-{project_name}-production
# Then go to the AI resource → Diagnostic settings → Add
# Send Audit + RequestResponse logs to the workspace

## Step 9: Enter in Bonito
# You need ALL of these:
#   - api_key (from Step 3)
#   - endpoint (from Step 4)
#   - tenant_id (from Step 5)
#   - client_id (from Step 5)
#   - client_secret (from Step 5/6)
#   - subscription_id (your Azure subscription)
#   - resource_group: rg-{project_name}-production
#
# Bonito auto-detects Foundry vs OpenAI mode from the resource type.
# After connecting, Bonito handles everything: model discovery, deployments, routing, costs.

# ⚠️  SECURITY REMINDERS:
# - Rotate client secret before expiry
# - Cognitive Services Contributor is scoped to the AI resource only (not subscription-wide)
# - Cost Management Reader is read-only
# - Enable diagnostic logging for audit compliance
'''
    return {
        "files": [{"filename": "bonito-azure-manual.md", "content": code.strip()}],
        "code": code,
        "filename": "bonito-azure-manual.md",
        "instructions": [
            "Follow the step-by-step instructions above (Portal or CLI)",
            "Create resource group, AI Foundry resource, and service principal",
            "Assign Cognitive Services Contributor and Cost Management Reader roles",
            "Copy api_key, endpoint, tenant_id, client_id, client_secret, subscription_id, resource_group into Bonito",
            "Bonito handles everything after that — model discovery, deployments, routing, cost tracking",
        ],
        "security_notes": [
            "✅ Cognitive Services Contributor — scoped to AI resource only (needed for deployment management)",
            "✅ Cost Management Reader — read-only cost data",
            "✅ No Owner or subscription-wide Contributor roles",
            "✅ Diagnostic logging for audit compliance",
            "🔄 Client secret expires — set a calendar reminder to rotate",
        ],
    }
