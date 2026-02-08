"""GCP IaC templates for Bonito onboarding.

Synced from bonito-infra/gcp/ — these are the production-tested Terraform files.
Generates least-privilege GCP configuration:
- Service account with Vertex AI User role (NOT Editor)
- Billing Viewer on billing account (not project-level)
- Audit logging for Vertex AI operations
- JSON key for authentication
"""

from typing import Optional


def generate_gcp_iac(iac_tool: str, **kwargs) -> dict:
    generators = {
        "terraform": _terraform,
        "pulumi": _pulumi,
        "manual": _manual,
    }
    gen = generators.get(iac_tool)
    if not gen:
        raise ValueError(f"GCP does not support IaC tool: {iac_tool}. Use: {list(generators.keys())}")
    return gen(**kwargs)


# ---------------------------------------------------------------------------
# Terraform — exact content from bonito-infra/gcp/
# ---------------------------------------------------------------------------

_TF_PROVIDERS = r'''terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Local backend by default
  backend "local" {
    path = "terraform.tfstate"
  }

  # GCS remote backend (uncomment to use):
  # backend "gcs" {
  #   bucket = "bonito-terraform-state"
  #   prefix = "gcp/terraform.tfstate"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
'''

_TF_VARIABLES = r'''variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "bonito"
}

variable "billing_account_id" {
  description = "GCP billing account ID (for billing viewer role)"
  type        = string
  default     = ""
}
'''

_TF_MAIN = r'''################################################################################
# Enable Required APIs
################################################################################

resource "google_project_service" "vertex_ai" {
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "resource_manager" {
  service            = "cloudresourcemanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "iam" {
  service            = "iam.googleapis.com"
  disable_on_destroy = false
}

################################################################################
# Service Account — Minimal permissions for Bonito
################################################################################

resource "google_service_account" "bonito" {
  account_id   = "${var.project_name}-sa"
  display_name = "Bonito AI Platform Service Account"
  description  = "Least-privilege SA for Bonito Vertex AI and billing access"

  depends_on = [google_project_service.iam]
}

# roles/aiplatform.user: Use Vertex AI models (NOT roles/editor)
resource "google_project_iam_member" "vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.bonito.email}"
}

# roles/billing.viewer: Read-only cost data
resource "google_billing_account_iam_member" "billing_viewer" {
  count              = var.billing_account_id != "" ? 1 : 0
  billing_account_id = var.billing_account_id
  role               = "roles/billing.viewer"
  member             = "serviceAccount:${google_service_account.bonito.email}"
}

################################################################################
# Service Account Key — For programmatic access
################################################################################

resource "google_service_account_key" "bonito" {
  service_account_id = google_service_account.bonito.name
  key_algorithm      = "KEY_ALG_RSA_2048"
}

# Write the key to a local file (gitignored)
resource "local_file" "sa_key" {
  content         = base64decode(google_service_account_key.bonito.private_key)
  filename        = "${path.module}/bonito-sa-key.json"
  file_permission = "0600"
}

################################################################################
# Audit Logging — Vertex AI data access logs
################################################################################

resource "google_project_iam_audit_config" "vertex_audit" {
  project = var.project_id
  service = "aiplatform.googleapis.com"

  audit_log_config {
    log_type = "ADMIN_READ"
  }

  audit_log_config {
    log_type = "DATA_READ"
  }

  audit_log_config {
    log_type = "DATA_WRITE"
  }
}
'''

_TF_OUTPUTS = r'''output "project_id" {
  description = "GCP project ID"
  value       = var.project_id
}

output "service_account_email" {
  description = "Bonito service account email"
  value       = google_service_account.bonito.email
}

output "key_file_path" {
  description = "Path to the service account JSON key file"
  value       = local_file.sa_key.filename
  sensitive   = true
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
        "filename": "bonito-gcp-terraform/",
        "instructions": [
            "Install Terraform >= 1.5.0 (https://terraform.io/downloads)",
            "Authenticate: `gcloud auth application-default login`",
            "Save all 4 files into a directory (or download the ZIP below)",
            "Run: `terraform init`",
            "Run: `terraform plan -var='project_id=YOUR_PROJECT_ID'`",
            "Run: `terraform apply -var='project_id=YOUR_PROJECT_ID'`",
            "The JSON key is saved to `bonito-sa-key.json` automatically",
            "Copy the project_id, service_account_email, and JSON key file into Bonito",
        ],
        "security_notes": [
            "✅ Vertex AI User role — predict + list only, not Editor",
            "✅ Billing Viewer on billing account (not project Editor)",
            "✅ Project-scoped — no org-wide access",
            "✅ Audit logging enabled for all Vertex AI operations",
            "✅ JSON key written with 0600 permissions",
            "🔄 Rotate JSON key every 90 days",
            "🔒 Never commit bonito-sa-key.json to git",
            "📋 Consider Workload Identity Federation for production",
        ],
    }


def _pulumi(project_name: str = "bonito", region: str = "us-central1", gcp_project_id: Optional[str] = None, **kwargs) -> dict:
    project = gcp_project_id or "YOUR_PROJECT_ID"
    code = f'''"""Bonito GCP Integration — Pulumi (Python)

Synced from bonito-infra patterns. Least-privilege service account.
Security: Vertex AI User (not Editor), Billing Viewer. Project-scoped only.

Run: pulumi up
"""

import pulumi
import pulumi_gcp as gcp

project_id = "{project}"

# --- Enable APIs ---
gcp.projects.Service("{project_name}-vertex-api",
    service="aiplatform.googleapis.com", disable_on_destroy=False)
gcp.projects.Service("{project_name}-iam-api",
    service="iam.googleapis.com", disable_on_destroy=False)
gcp.projects.Service("{project_name}-crm-api",
    service="cloudresourcemanager.googleapis.com", disable_on_destroy=False)

# --- Service Account ---
sa = gcp.serviceaccount.Account("{project_name}-sa",
    account_id="{project_name}-sa",
    display_name="Bonito AI Platform Service Account",
    description="Least-privilege: Vertex AI User + Billing Viewer")

# --- Vertex AI User (NOT Editor) ---
gcp.projects.IAMMember("{project_name}-vertex-user",
    project=project_id, role="roles/aiplatform.user",
    member=sa.email.apply(lambda e: f"serviceAccount:{{e}}"))

# --- JSON Key ---
key = gcp.serviceaccount.Key("{project_name}-key",
    service_account_id=sa.name, key_algorithm="KEY_ALG_RSA_2048")

# --- Audit Logging ---
gcp.projects.IAMAuditConfig("{project_name}-audit",
    project=project_id, service="aiplatform.googleapis.com",
    audit_log_configs=[
        gcp.projects.IAMAuditConfigAuditLogConfigArgs(log_type="ADMIN_READ"),
        gcp.projects.IAMAuditConfigAuditLogConfigArgs(log_type="DATA_READ"),
        gcp.projects.IAMAuditConfigAuditLogConfigArgs(log_type="DATA_WRITE"),
    ])

pulumi.export("project_id", project_id)
pulumi.export("service_account_email", sa.email)
pulumi.export("key_json_base64", key.private_key)
'''
    return {
        "files": [{"filename": "__main__.py", "content": code.strip()}],
        "code": code,
        "filename": "__main__.py",
        "instructions": [
            "Install Pulumi (https://www.pulumi.com/docs/install/)",
            "Run: `pulumi new gcp-python`",
            "Replace `__main__.py` with this code (update project_id)",
            "Run: `gcloud auth application-default login`",
            "Run: `pulumi up`",
            "Decode the key: `pulumi stack output key_json_base64 | base64 -d > bonito-sa-key.json`",
            "Copy the project_id, service_account_email, and JSON key into Bonito",
        ],
        "security_notes": [
            "✅ Vertex AI User — not Editor",
            "✅ Project-scoped, not org-wide",
            "✅ Audit logging enabled",
            "🔄 Rotate JSON key every 90 days",
            "🔒 Never commit the key file to git",
        ],
    }


def _manual(project_name: str = "bonito", gcp_project_id: Optional[str] = None, **kwargs) -> dict:
    project = gcp_project_id or "YOUR_PROJECT_ID"
    code = f'''# Bonito GCP Setup — Manual Instructions
# ========================================
# Synced from bonito-infra patterns.
# Total time: ~10 minutes

## Step 1: Enable Required APIs

gcloud services enable aiplatform.googleapis.com --project={project}
gcloud services enable iam.googleapis.com --project={project}
gcloud services enable cloudresourcemanager.googleapis.com --project={project}

## Step 2: Create Service Account

gcloud iam service-accounts create {project_name}-sa \\
  --display-name="Bonito AI Platform Service Account" \\
  --description="Least-privilege: Vertex AI User + Billing Viewer" \\
  --project={project}

## Step 3: Assign Roles (Least Privilege)

### Vertex AI User (NOT Editor)
gcloud projects add-iam-policy-binding {project} \\
  --member="serviceAccount:{project_name}-sa@{project}.iam.gserviceaccount.com" \\
  --role="roles/aiplatform.user"

### Billing Viewer (optional, requires billing account ID)
# gcloud billing accounts add-iam-policy-binding BILLING_ACCOUNT_ID \\
#   --member="serviceAccount:{project_name}-sa@{project}.iam.gserviceaccount.com" \\
#   --role="roles/billing.viewer"

## Step 4: Create JSON Key

gcloud iam service-accounts keys create bonito-sa-key.json \\
  --iam-account={project_name}-sa@{project}.iam.gserviceaccount.com
chmod 600 bonito-sa-key.json

## Step 5: Enable Audit Logging
# Go to: IAM & Admin → Audit Logs
# Find "Vertex AI API" → Enable Admin Read, Data Read, Data Write

## Step 6: Enter in Bonito
# You need: project_id, service_account_email, and the JSON key file contents

# ⚠️  SECURITY REMINDERS:
# - NEVER commit bonito-sa-key.json to git
# - Rotate the key every 90 days
# - Vertex AI User is project-scoped — cannot access other projects
# - Consider Workload Identity Federation for production
'''
    return {
        "files": [{"filename": "bonito-gcp-manual.sh", "content": code.strip()}],
        "code": code,
        "filename": "bonito-gcp-manual.sh",
        "instructions": [
            "Install gcloud CLI (https://cloud.google.com/sdk/docs/install)",
            "Run: `gcloud auth login`",
            "Run the commands above in order",
            "Copy the project_id, service_account_email, and JSON key into Bonito",
        ],
        "security_notes": [
            "✅ Vertex AI User — not Editor or Owner",
            "✅ Project-scoped — no org-wide access",
            "✅ Audit logging enabled for compliance",
            "🔄 Rotate JSON key every 90 days",
            "🔒 Never commit the key file to version control",
        ],
    }
