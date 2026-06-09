# Provisioning Azure for Bonito — Terraform on Windows

End-to-end walkthrough for a Windows user (PowerShell) to stand up an Azure AI / OpenAI environment for Bonito using the `bonito-infra/azure` Terraform module. Replaces the manual portal-clicking flow with `terraform apply`.

**Time to first `bonito providers add azure`:** ~25 minutes (longer the first time you set up the tooling, ~10 minutes once familiar).

---

## What this gives you

Running this Terraform produces, in your own Azure tenant/subscription:

- A resource group (`rg-{project}-{environment}`)
- An **Azure OpenAI cognitive account** with public network access (this is what Bonito calls)
- A **service principal** (Microsoft Entra app registration + client secret) Bonito uses to authenticate
- RBAC: either managed (`Cognitive Services Contributor`) or a least-privilege custom role
- `Cost Management Reader` role on the subscription (for Bonito's cost analytics)
- A Log Analytics workspace + diagnostic settings on the AI account (audit + request/response logs)
- Outputs printed at the end with everything you need for `bonito providers add azure`

You will **not** need to click around in the Azure portal once this is set up.

---

## Prerequisites

- A Windows 10/11 machine with admin rights
- An **Azure subscription** you own (or are at least `Owner` on)
- A **Microsoft account** with sign-in to that subscription
- ~5 GB free disk (most of which is Azure CLI's dependencies)

---

## Step 1 — Install the tooling

### 1a. Install Chocolatey (one-time)

Open **PowerShell as Administrator**:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

Close and reopen PowerShell after this finishes.

### 1b. Install Terraform, Azure CLI, and Git

```powershell
choco install terraform azure-cli git -y
```

Close and reopen PowerShell **again** (the installers add things to `PATH`).

Verify everything is installed:

```powershell
terraform -version
az --version
git --version
```

All three should print version numbers without errors.

**If you don't want Chocolatey:**

- Terraform: https://developer.hashicorp.com/terraform/install (download the Windows AMD64 zip, extract to `C:\Terraform`, add to `PATH`)
- Azure CLI: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows (use the MSI installer)
- Git: https://git-scm.com/download/win

---

## Step 2 — Sign in to Azure

```powershell
az login
```

A browser tab will open. Sign in with the account that owns the target Azure subscription.

After login, set the subscription Terraform should target. List them first:

```powershell
az account list --output table
```

Note the `SubscriptionId` column for the one you want. Then:

```powershell
az account set --subscription "<SUBSCRIPTION_ID>"
```

Confirm:

```powershell
az account show --output table
```

The `IsDefault` column should be `True` for the right subscription.

---

## Step 3 — Get the Bonito Terraform module

```powershell
# Pick a directory you're comfortable with
mkdir C:\bonito-infra
cd C:\bonito-infra

# Clone (if Shabari shared the repo with you; otherwise ask him for an export)
git clone <repo-url> .

cd azure
```

You should now see:

```
main.tf
variables.tf
outputs.tf
providers.tf
```

---

## Step 4 — Create your `terraform.tfvars`

The module is parameterized so you don't have to edit `main.tf`. Create a new file `terraform.tfvars` in the `azure` folder:

```powershell
notepad terraform.tfvars
```

Paste this in and edit the values:

```hcl
# Your Azure subscription ID
subscription_id   = "00000000-0000-0000-0000-000000000000"

# Naming — these become resource name prefixes
project_name      = "oaksparrow"   # short, lowercase, no spaces
environment       = "prod"          # prod | staging | dev

# Region — pick one with Azure OpenAI availability
# Safe defaults: eastus2, swedencentral, francecentral, australiaeast
location          = "eastus2"

# RBAC mode
# "managed"          = use Azure's built-in "Cognitive Services Contributor" role (faster setup)
# "least_privilege"  = use a custom role with only the exact permissions Bonito needs (enterprise-grade)
rbac_mode         = "managed"

# SKU for the Cognitive Services account
# "S0" is the standard tier; this is almost always what you want
cognitive_services_sku = "S0"

# Knowledge Base wiring (set false unless you have a specific blob container to grant Bonito access to)
enable_knowledge_base = false
kb_storage_account    = ""
kb_container_name     = ""
```

Save and close Notepad.

**Important:** don't commit this file to git — it has your subscription ID. The repo's `.gitignore` already excludes `*.tfvars`, but double-check before pushing if you fork.

---

## Step 5 — Run Terraform

```powershell
# Download the Azure provider plugins
terraform init

# Show what will be created — read this output
terraform plan

# Actually create everything
terraform apply
```

`terraform apply` will print a summary and ask `Enter a value:` — type `yes` and press Enter.

It will take **~3 to 5 minutes** to create the cognitive account. You'll see live status as resources come up.

---

## Step 6 — Grab the outputs

When `apply` finishes, run:

```powershell
terraform output
```

You'll see something like:

```
client_id                   = "d55ca9d9-12ce-4a95-bf60-bfcef5da0c33"
client_secret               = <sensitive>
cognitive_account_endpoint  = "https://oaksparrow-ai-prod.openai.azure.com/"
resource_group_name         = "rg-oaksparrow-prod"
subscription_id             = "00000000-0000-0000-0000-000000000000"
tenant_id                   = "4d1f0f00-2a1c-4075-ae52-627926e621d3"
```

To reveal the (sensitive) client secret:

```powershell
terraform output -raw client_secret
```

**Copy that value to a password manager immediately.** Terraform stores it in `terraform.tfstate`, but treat it like any other secret — back it up safely.

---

## Step 7 — Deploy at least one model

Without an actual model deployment, Bonito will connect successfully but won't route any traffic.

Use the Azure CLI to deploy a model. `gpt-4o-mini` is the cheapest broadly-available option:

```powershell
$RG = terraform output -raw resource_group_name
$AI = "$(terraform output -raw cognitive_account_endpoint)".Replace("https://","").Split(".")[0]

az cognitiveservices account deployment create `
  --name $AI `
  --resource-group $RG `
  --deployment-name gpt-4o-mini `
  --model-name gpt-4o-mini `
  --model-version "2024-07-18" `
  --model-format OpenAI `
  --sku-name Standard `
  --sku-capacity 10
```

This takes ~30 seconds. Use the deployment name you choose (`gpt-4o-mini` here) as the model identifier in Bonito.

To deploy more models later, re-run the command with a different `--model-name` / `--deployment-name`.

---

## Step 8 — Connect to Bonito

Install the Bonito CLI if you haven't:

```powershell
pip install bonito-cli
bonito auth login
```

Then add the Azure provider. Pull the values straight from Terraform outputs:

```powershell
bonito providers add azure `
  --tenant-id (terraform output -raw tenant_id) `
  --client-id (terraform output -raw client_id) `
  --client-secret (terraform output -raw client_secret) `
  --subscription-id (terraform output -raw subscription_id) `
  --endpoint (terraform output -raw cognitive_account_endpoint) `
  --region eastus2 `
  --name "Azure (Oak & Sparrow Prod)"
```

If it prints **"connection validated"**, you're done. If it errors with `SubscriptionNotFound`, give Azure another 60 seconds for RBAC propagation and try again.

---

## Step 9 — Verify end-to-end

```powershell
bonito providers list
bonito models list --provider azure
```

You should see your `gpt-4o-mini` deployment in the model list. Test inference:

```powershell
bonito gateway test --model gpt-4o-mini --prompt "Say hello in 5 words"
```

If you get a response, everything is wired up. You can now mint gateway keys, build agents, etc.

---

## Updating later

Add a new model deployment? `az cognitiveservices account deployment create` again (Step 7), then in Bonito:

```powershell
bonito models sync --provider azure
```

Rotate the client secret? Re-run `terraform apply` with a forced replace:

```powershell
terraform apply -replace=azuread_application_password.bonito
```

Then update the secret in Bonito:

```powershell
bonito providers update azure --client-secret (terraform output -raw client_secret)
```

Tear it all down (deletes the Azure resources):

```powershell
terraform destroy
```

---

## Common Windows gotchas

| Symptom | Fix |
|---|---|
| `terraform` not recognized after install | Close and reopen PowerShell. `PATH` changes don't apply to existing sessions. |
| Backtick (`) line continuation doesn't work | You typed a regular quote instead of a backtick. The backtick is the key above Tab. |
| `az login` opens the wrong account | Run `az logout` first. Or use `az login --use-device-code` if your browser is confused. |
| `terraform apply` fails with `ResourceGroupNotFound` | RBAC propagation lag. Wait 60 seconds and retry — Azure can take that long to recognize new role assignments. |
| Chocolatey command fails with execution policy errors | Make sure you opened PowerShell **as Administrator** for the install commands. |
| Bonito CLI errors with `Connection refused` | The CLI defaults to `https://api.getbonito.com`. If you're using a self-hosted Bonito, set `$env:BONITO_API_URL = "https://your-host"` before `bonito auth login`. |
| Terraform state file lives in plaintext | This is normal. For a team, set up a remote backend (Azure Storage Account + state lock). Single-developer use is fine local. |

---

## Cost expectations

The Terraform module itself provisions only the Azure OpenAI account, Log Analytics workspace, RBAC, and identity resources. **None of these have monthly fixed costs** except Log Analytics (~$2-5/month for low-volume audit logs).

Real costs start when you deploy models and call them — that's pay-as-you-go per token, billed at Azure's published rates.

---

## What was created where (cheat sheet)

| Thing | Where in Azure | Why Bonito needs it |
|---|---|---|
| Resource group `rg-{project}-{env}` | Azure subscription | Container for everything |
| Cognitive Services account | Inside that RG | The actual Azure OpenAI endpoint |
| Microsoft Entra application | Tenant level | The service principal Bonito uses to call Azure |
| Application password | Tied to the app | The client secret Bonito stores |
| Role assignment (Cognitive Services Contributor) | On the cognitive account | Lets the SP create/manage deployments and call models |
| Role assignment (Cost Management Reader) | On the subscription | Lets Bonito show your Azure costs in the dashboard |
| Log Analytics workspace | Inside the RG | Audit + request/response logs |
| Diagnostic setting | On the cognitive account | Wires the audit logs into the workspace |

---

If something goes sideways and you can't recover, message Shabari with the output of `terraform plan` and the error from `terraform apply` and we'll figure it out together.
