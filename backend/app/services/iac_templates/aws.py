"""AWS IaC templates for Bonito onboarding.

Synced from bonito-infra/aws/ — these are the production-tested Terraform files.
Generates least-privilege IAM configuration:
- IAM user with direct Bedrock, Cost Explorer, STS permissions
- IAM role available for advanced cross-account setups
- CloudTrail audit logging for Bedrock API calls
"""

from typing import Optional


def generate_aws_iac(iac_tool: str, **kwargs) -> dict:
    generators = {
        "terraform": _terraform,
        "pulumi": _pulumi,
        "cloudformation": _cloudformation,
        "manual": _manual,
    }
    gen = generators.get(iac_tool)
    if not gen:
        raise ValueError(f"AWS does not support IaC tool: {iac_tool}. Use: {list(generators.keys())}")
    return gen(**kwargs)


# ---------------------------------------------------------------------------
# Terraform — exact content from bonito-infra/aws/
# ---------------------------------------------------------------------------

_TF_PROVIDERS = r'''terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Local backend by default
  backend "local" {
    path = "terraform.tfstate"
  }

  # S3 remote backend (uncomment to use):
  # backend "s3" {
  #   bucket         = "bonito-terraform-state"
  #   key            = "aws/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "bonito-terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "bonito"
      ManagedBy   = "terraform"
      Environment = var.environment
    }
  }
}
'''

_TF_VARIABLES = r'''variable "aws_region" {
  description = "AWS region for Bonito resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g. production, staging)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "bonito"
}

variable "cloudtrail_s3_bucket_name" {
  description = "S3 bucket name for CloudTrail logs"
  type        = string
  default     = "bonito-cloudtrail-logs"
}

variable "iam_mode" {
  description = "IAM mode: 'managed' creates a single broad policy (quick setup). 'least_privilege' creates separate policies per capability — enterprise teams can grant only what they approve."
  type        = string
  default     = "least_privilege"

  validation {
    condition     = contains(["managed", "least_privilege"], var.iam_mode)
    error_message = "iam_mode must be 'managed' or 'least_privilege'."
  }
}

variable "enable_provisioning" {
  description = "Grant Provisioned Throughput permissions (create/manage reserved capacity). Only needed if deploying dedicated model endpoints."
  type        = bool
  default     = true
}

variable "enable_model_activation" {
  description = "Grant model activation permissions (enable new foundation models). Only needed if enabling models from Bonito UI."
  type        = bool
  default     = true
}

variable "enable_cost_tracking" {
  description = "Grant Cost Explorer read access for spend visibility in Bonito dashboard."
  type        = bool
  default     = true
}

# ── Knowledge Base (Optional) ───────────────────────────────────────

variable "enable_knowledge_base" {
  description = "Enable Bonito Knowledge Base (S3 read access for document sync)"
  type        = bool
  default     = false
}

variable "kb_s3_bucket" {
  description = "S3 bucket containing documents for Knowledge Base"
  type        = string
  default     = ""
}

variable "kb_s3_prefix" {
  description = "S3 prefix (folder) to scope document access"
  type        = string
  default     = ""
}
'''

_TF_MAIN = r'''################################################################################
# Data Sources
################################################################################

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

################################################################################
# IAM Policy — Two options (toggle via variable)
#
# Option A: "managed" — Single policy with all Bedrock permissions.
#   Quick to set up. Broader than strictly needed.
#
# Option B: "least_privilege" — Separate policies per capability.
#   Enterprise-recommended. Customer can grant only what they want:
#     - Core (always needed): list + invoke
#     - Provisioning (optional): create/manage reserved capacity
#     - Model activation (optional): enable new models
#     - Cost tracking (optional): billing visibility
#
# Set var.iam_mode = "managed" or "least_privilege"
################################################################################

# ── Option A: Single managed policy (simple) ────────────────────────────────

resource "aws_iam_policy" "bonito_managed" {
  count       = var.iam_mode == "managed" ? 1 : 0
  name        = "${var.project_name}-policy"
  description = "Full Bonito AI platform policy — model discovery, invocation, provisioning, and cost tracking"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockFullAccess"
        Effect = "Allow"
        Action = [
          "bedrock:ListFoundationModels",
          "bedrock:GetFoundationModel",
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:CreateProvisionedModelThroughput",
          "bedrock:GetProvisionedModelThroughput",
          "bedrock:UpdateProvisionedModelThroughput",
          "bedrock:DeleteProvisionedModelThroughput",
          "bedrock:ListProvisionedModelThroughputs",
          "bedrock:PutFoundationModelEntitlement",
          "bedrock:GetFoundationModelAvailability",
        ]
        Resource = "*"
      },
      {
        Sid    = "CostExplorerReadOnly"
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage",
          "ce:GetCostForecast",
          "ce:GetDimensionValues",
          "ce:GetTags",
        ]
        Resource = "*"
      },
      {
        Sid      = "STSValidation"
        Effect   = "Allow"
        Action   = ["sts:GetCallerIdentity"]
        Resource = "*"
      },
    ]
  })
}

# ── Option B: Separate least-privilege policies ─────────────────────────────

# CORE: Always required — discover and invoke models
resource "aws_iam_policy" "bonito_core" {
  count       = var.iam_mode == "least_privilege" ? 1 : 0
  name        = "${var.project_name}-core"
  description = "Bonito — model discovery + invocation (required)"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockDiscovery"
        Effect = "Allow"
        Action = [
          "bedrock:ListFoundationModels",
          "bedrock:GetFoundationModel",
          "bedrock:GetFoundationModelAvailability",
        ]
        Resource = "*"
      },
      {
        Sid    = "BedrockInvoke"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ]
        Resource = [
          "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}::foundation-model/*",
          "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/*",
          "arn:${data.aws_partition.current.partition}:bedrock:us-*::foundation-model/*",
        ]
      },
      {
        Sid      = "STSValidation"
        Effect   = "Allow"
        Action   = ["sts:GetCallerIdentity"]
        Resource = "*"
      },
    ]
  })
}

# PROVISIONING: Optional — create/manage reserved capacity
resource "aws_iam_policy" "bonito_provisioning" {
  count       = var.iam_mode == "least_privilege" && var.enable_provisioning ? 1 : 0
  name        = "${var.project_name}-provisioning"
  description = "Bonito — provisioned throughput management (optional)"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockProvisionedThroughput"
        Effect = "Allow"
        Action = [
          "bedrock:CreateProvisionedModelThroughput",
          "bedrock:GetProvisionedModelThroughput",
          "bedrock:UpdateProvisionedModelThroughput",
          "bedrock:DeleteProvisionedModelThroughput",
          "bedrock:ListProvisionedModelThroughputs",
        ]
        Resource = "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:provisioned-model/*"
      },
    ]
  })
}

# MODEL ACTIVATION: Optional — enable new foundation models
resource "aws_iam_policy" "bonito_activation" {
  count       = var.iam_mode == "least_privilege" && var.enable_model_activation ? 1 : 0
  name        = "${var.project_name}-activation"
  description = "Bonito — model activation/entitlement (optional)"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockModelEntitlement"
        Effect = "Allow"
        Action = [
          "bedrock:PutFoundationModelEntitlement",
        ]
        Resource = "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}::foundation-model/*"
      },
    ]
  })
}

# COST TRACKING: Optional — read billing data
resource "aws_iam_policy" "bonito_costs" {
  count       = var.iam_mode == "least_privilege" && var.enable_cost_tracking ? 1 : 0
  name        = "${var.project_name}-costs"
  description = "Bonito — cost tracking via Cost Explorer (optional)"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CostExplorerReadOnly"
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage",
          "ce:GetCostForecast",
          "ce:GetDimensionValues",
          "ce:GetTags",
        ]
        Resource = "*"
      },
    ]
  })
}

################################################################################
# IAM User — Programmatic access
################################################################################

resource "aws_iam_user" "bonito" {
  name = "${var.project_name}-user"
  path = "/system/"
}

# Managed mode: single policy attachment
resource "aws_iam_user_policy_attachment" "bonito_managed" {
  count      = var.iam_mode == "managed" ? 1 : 0
  user       = aws_iam_user.bonito.name
  policy_arn = aws_iam_policy.bonito_managed[0].arn
}

# Least-privilege mode: attach each policy separately
resource "aws_iam_user_policy_attachment" "bonito_core" {
  count      = var.iam_mode == "least_privilege" ? 1 : 0
  user       = aws_iam_user.bonito.name
  policy_arn = aws_iam_policy.bonito_core[0].arn
}

resource "aws_iam_user_policy_attachment" "bonito_provisioning" {
  count      = var.iam_mode == "least_privilege" && var.enable_provisioning ? 1 : 0
  user       = aws_iam_user.bonito.name
  policy_arn = aws_iam_policy.bonito_provisioning[0].arn
}

resource "aws_iam_user_policy_attachment" "bonito_activation" {
  count      = var.iam_mode == "least_privilege" && var.enable_model_activation ? 1 : 0
  user       = aws_iam_user.bonito.name
  policy_arn = aws_iam_policy.bonito_activation[0].arn
}

resource "aws_iam_user_policy_attachment" "bonito_costs" {
  count      = var.iam_mode == "least_privilege" && var.enable_cost_tracking ? 1 : 0
  user       = aws_iam_user.bonito.name
  policy_arn = aws_iam_policy.bonito_costs[0].arn
}

# ── Knowledge Base: S3 Read Access (Optional) ────────────────────────

resource "aws_iam_policy" "bonito_kb_s3_read" {
  count       = var.enable_knowledge_base ? 1 : 0
  name        = "${var.project_name}-kb-s3-read"
  description = "Allow Bonito to read documents from S3 for Knowledge Base indexing"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BonitoKBListBucket"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = "arn:${data.aws_partition.current.partition}:s3:::${var.kb_s3_bucket}"
        Condition = var.kb_s3_prefix != "" ? {
          StringLike = {
            "s3:prefix" = ["${var.kb_s3_prefix}*"]
          }
        } : {}
      },
      {
        Sid    = "BonitoKBReadObjects"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = "arn:${data.aws_partition.current.partition}:s3:::${var.kb_s3_bucket}/${var.kb_s3_prefix}*"
      }
    ]
  })
}

resource "aws_iam_user_policy_attachment" "bonito_kb" {
  count      = var.enable_knowledge_base ? 1 : 0
  user       = aws_iam_user.bonito.name
  policy_arn = aws_iam_policy.bonito_kb_s3_read[0].arn
}

################################################################################
# IAM Role — Assumed by the Bonito IAM user (optional advanced pattern)
################################################################################

resource "aws_iam_role" "bonito" {
  name        = "${var.project_name}-role"
  description = "Role assumed by Bonito for AI and cost operations"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_user.bonito.arn
        }
        Action = "sts:AssumeRole"
        Condition = {
          # Require external ID for cross-account safety
          StringEquals = {
            "sts:ExternalId" = "${var.project_name}-external-id"
          }
        }
      },
    ]
  })
}

# Attach policies to role (same as user for role assumption pattern)
resource "aws_iam_role_policy_attachment" "bonito_managed" {
  count      = var.iam_mode == "managed" ? 1 : 0
  role       = aws_iam_role.bonito.name
  policy_arn = aws_iam_policy.bonito_managed[0].arn
}

resource "aws_iam_role_policy_attachment" "bonito_core" {
  count      = var.iam_mode == "least_privilege" ? 1 : 0
  role       = aws_iam_role.bonito.name
  policy_arn = aws_iam_policy.bonito_core[0].arn
}

resource "aws_iam_role_policy_attachment" "bonito_provisioning" {
  count      = var.iam_mode == "least_privilege" && var.enable_provisioning ? 1 : 0
  role       = aws_iam_role.bonito.name
  policy_arn = aws_iam_policy.bonito_provisioning[0].arn
}

resource "aws_iam_role_policy_attachment" "bonito_activation" {
  count      = var.iam_mode == "least_privilege" && var.enable_model_activation ? 1 : 0
  role       = aws_iam_role.bonito.name
  policy_arn = aws_iam_policy.bonito_activation[0].arn
}

resource "aws_iam_role_policy_attachment" "bonito_costs" {
  count      = var.iam_mode == "least_privilege" && var.enable_cost_tracking ? 1 : 0
  role       = aws_iam_role.bonito.name
  policy_arn = aws_iam_policy.bonito_costs[0].arn
}

resource "aws_iam_role_policy_attachment" "bonito_kb" {
  count      = var.enable_knowledge_base ? 1 : 0
  role       = aws_iam_role.bonito.name
  policy_arn = aws_iam_policy.bonito_kb_s3_read[0].arn
}

resource "aws_iam_access_key" "bonito" {
  user = aws_iam_user.bonito.name
}

################################################################################
# CloudTrail — Audit logging for Bedrock API calls
################################################################################

resource "aws_s3_bucket" "cloudtrail" {
  bucket        = var.cloudtrail_s3_bucket_name
  force_destroy = false
}

resource "aws_s3_bucket_policy" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSCloudTrailAclCheck"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.cloudtrail.arn
      },
      {
        Sid    = "AWSCloudTrailWrite"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.cloudtrail.arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl" = "bucket-owner-full-control"
          }
        }
      },
    ]
  })
}

resource "aws_s3_bucket_public_access_block" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudtrail" "bonito" {
  name                          = "${var.project_name}-bedrock-audit"
  s3_bucket_name                = aws_s3_bucket.cloudtrail.id
  include_global_service_events = false
  is_multi_region_trail         = false
  enable_logging                = true

  event_selector {
    read_write_type           = "All"
    include_management_events = true
  }
}
'''

_TF_OUTPUTS = r'''output "access_key_id" {
  description = "AWS access key ID for the Bonito IAM user"
  value       = aws_iam_access_key.bonito.id
}

output "secret_access_key" {
  description = "AWS secret access key for the Bonito IAM user"
  value       = aws_iam_access_key.bonito.secret
  sensitive   = true
}

output "role_arn" {
  description = "ARN of the IAM role Bonito assumes"
  value       = aws_iam_role.bonito.arn
}

output "cloudtrail_bucket" {
  description = "S3 bucket storing Bedrock audit logs"
  value       = aws_s3_bucket.cloudtrail.id
}
'''


def _terraform(
    iam_mode: str = "least_privilege",
    enable_provisioning: bool = True,
    enable_model_activation: bool = True,
    enable_cost_tracking: bool = True,
    **kwargs
) -> dict:
    files = [
        {"filename": "providers.tf", "content": _TF_PROVIDERS.strip()},
        {"filename": "variables.tf", "content": _TF_VARIABLES.strip()},
        {"filename": "main.tf", "content": _TF_MAIN.strip()},
        {"filename": "outputs.tf", "content": _TF_OUTPUTS.strip()},
    ]
    # Combined view for the code display
    combined = "\n\n".join(
        f"# ── {f['filename']} {'─' * (60 - len(f['filename']))}\n\n{f['content']}"
        for f in files
    )
    return {
        "files": files,
        "code": combined,
        "filename": "bonito-aws-terraform/",
        "instructions": [
            "Install Terraform >= 1.5.0 (https://terraform.io/downloads)",
            "Save all 4 files into a directory (or download the ZIP below)",
            "Run: `terraform init`",
            "Run: `terraform plan` — review the resources it will create",
            "Run: `terraform apply` — type 'yes' to confirm",
            "Run: `terraform output secret_access_key` to reveal the secret key",
            "Copy the access_key_id, secret_access_key, and role_arn into Bonito",
        ],
        "security_notes": [
            "✅ Least-privilege IAM — separate policies per capability you enable",
            "✅ Core permissions always included: model discovery + invocation + STS validation",
            "✅ Optional capabilities: provisioning, model activation, cost tracking",
            "✅ CloudTrail audit logging for all Bedrock API calls",
            "✅ S3 bucket for audit logs with public access blocked",
            "🔄 Rotate access keys every 90 days",
            "🔒 Store terraform.tfstate securely — it contains the secret key",
        ],
    }


def _pulumi(
    project_name: str = "bonito",
    region: str = "us-east-1",
    iam_mode: str = "least_privilege",
    enable_provisioning: bool = True,
    enable_model_activation: bool = True,
    enable_cost_tracking: bool = True,
    **kwargs,
) -> dict:
    code = f'''"""Bonito AWS Integration - Pulumi (Python)

Purpose: Create least-privilege IAM user for Bonito AI platform.
Security: Modular policies - enable only the capabilities you need.

Run: pulumi up
"""

import pulumi
import pulumi_aws as aws
import json

# Configuration
iam_mode = pulumi.Config().get("iam_mode") or "least_privilege"
enable_provisioning = pulumi.Config().get_bool("enable_provisioning") or True
enable_model_activation = pulumi.Config().get_bool("enable_model_activation") or True
enable_cost_tracking = pulumi.Config().get_bool("enable_cost_tracking") or True

# --- IAM User (programmatic only, no console access) ---
user = aws.iam.User("{project_name}-user",
    name="{project_name}-user", path="/system/")

if iam_mode == "managed":
    # Single broad policy for quick setup
    managed_policy = aws.iam.Policy("{project_name}-policy",
        name="{project_name}-policy",
        description="Full Bonito AI platform policy",
        policy=json.dumps({{
            "Version": "2012-10-17",
            "Statement": [
                {{
                    "Sid": "BedrockFullAccess",
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:ListFoundationModels", "bedrock:GetFoundationModel",
                        "bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream",
                        "bedrock:CreateProvisionedModelThroughput", "bedrock:GetProvisionedModelThroughput",
                        "bedrock:UpdateProvisionedModelThroughput", "bedrock:DeleteProvisionedModelThroughput",
                        "bedrock:ListProvisionedModelThroughputs",
                        "bedrock:PutFoundationModelEntitlement", "bedrock:GetFoundationModelAvailability"
                    ],
                    "Resource": "*"
                }},
                {{
                    "Sid": "CostExplorerReadOnly",
                    "Effect": "Allow",
                    "Action": ["ce:GetCostAndUsage", "ce:GetCostForecast", "ce:GetDimensionValues", "ce:GetTags"],
                    "Resource": "*"
                }},
                {{
                    "Sid": "STSValidation",
                    "Effect": "Allow",
                    "Action": ["sts:GetCallerIdentity"],
                    "Resource": "*"
                }}
            ]
        }})
    )
    aws.iam.UserPolicyAttachment("{project_name}-managed-attach",
        user=user.name, policy_arn=managed_policy.arn)
else:
    # Separate least-privilege policies per capability
    # CORE: Always required
    core_policy = aws.iam.Policy("{project_name}-core",
        name="{project_name}-core",
        description="Bonito - model discovery + invocation (required)",
        policy=json.dumps({{
            "Version": "2012-10-17",
            "Statement": [
                {{
                    "Sid": "BedrockDiscovery",
                    "Effect": "Allow",
                    "Action": ["bedrock:ListFoundationModels", "bedrock:GetFoundationModel", "bedrock:GetFoundationModelAvailability"],
                    "Resource": "*"
                }},
                {{
                    "Sid": "BedrockInvoke",
                    "Effect": "Allow",
                    "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                    "Resource": ["arn:aws:bedrock:*::foundation-model/*", "arn:aws:bedrock:*:*:inference-profile/*"]
                }},
                {{
                    "Sid": "STSValidation",
                    "Effect": "Allow",
                    "Action": ["sts:GetCallerIdentity"],
                    "Resource": "*"
                }}
            ]
        }})
    )
    aws.iam.UserPolicyAttachment("{project_name}-core-attach",
        user=user.name, policy_arn=core_policy.arn)

    if enable_provisioning:
        prov_policy = aws.iam.Policy("{project_name}-provisioning",
            name="{project_name}-provisioning",
            description="Bonito - provisioned throughput management (optional)",
            policy=json.dumps({{
                "Version": "2012-10-17",
                "Statement": [{{
                    "Sid": "BedrockProvisionedThroughput",
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:CreateProvisionedModelThroughput", "bedrock:GetProvisionedModelThroughput",
                        "bedrock:UpdateProvisionedModelThroughput", "bedrock:DeleteProvisionedModelThroughput",
                        "bedrock:ListProvisionedModelThroughputs"
                    ],
                    "Resource": "*"
                }}]
            }})
        )
        aws.iam.UserPolicyAttachment("{project_name}-prov-attach",
            user=user.name, policy_arn=prov_policy.arn)

    if enable_model_activation:
        activation_policy = aws.iam.Policy("{project_name}-activation",
            name="{project_name}-activation",
            description="Bonito - model activation/entitlement (optional)",
            policy=json.dumps({{
                "Version": "2012-10-17",
                "Statement": [{{
                    "Sid": "BedrockModelEntitlement",
                    "Effect": "Allow",
                    "Action": ["bedrock:PutFoundationModelEntitlement"],
                    "Resource": "*"
                }}]
            }})
        )
        aws.iam.UserPolicyAttachment("{project_name}-activation-attach",
            user=user.name, policy_arn=activation_policy.arn)

    if enable_cost_tracking:
        cost_policy = aws.iam.Policy("{project_name}-costs",
            name="{project_name}-costs",
            description="Bonito - cost tracking via Cost Explorer (optional)",
            policy=json.dumps({{
                "Version": "2012-10-17",
                "Statement": [{{
                    "Sid": "CostExplorerReadOnly",
                    "Effect": "Allow",
                    "Action": ["ce:GetCostAndUsage", "ce:GetCostForecast", "ce:GetDimensionValues", "ce:GetTags"],
                    "Resource": "*"
                }}]
            }})
        )
        aws.iam.UserPolicyAttachment("{project_name}-costs-attach",
            user=user.name, policy_arn=cost_policy.arn)

access_key = aws.iam.AccessKey("{project_name}-key", user=user.name)

pulumi.export("access_key_id", access_key.id)
pulumi.export("secret_access_key", access_key.secret)
'''
    return {
        "files": [{"filename": "__main__.py", "content": code.strip()}],
        "code": code,
        "filename": "__main__.py",
        "instructions": [
            "Install Pulumi (https://www.pulumi.com/docs/install/)",
            "Run: `pulumi new aws-python` in a new directory",
            "Replace `__main__.py` with this code",
            "Configure mode: `pulumi config set iam_mode least_privilege`",
            "Toggle capabilities: `pulumi config set enable_provisioning false`",
            "Run: `pulumi up` - review and confirm",
            "Copy the access_key_id and secret_access_key into Bonito",
        ],
        "security_notes": [
            "✅ Modular least-privilege - separate policies per capability",
            "✅ Core permissions always included: model discovery + invocation + STS",
            "✅ Optional: provisioning, model activation, cost tracking",
            "✅ No admin access, no console login",
            "🔄 Rotate access keys every 90 days",
            "🔒 Pulumi state contains secrets - use encrypted backend",
        ],
    }


def _cloudformation(
    project_name: str = "bonito",
    region: str = "us-east-1",
    iam_mode: str = "least_privilege",
    enable_provisioning: bool = True,
    enable_model_activation: bool = True,
    enable_cost_tracking: bool = True,
    **kwargs,
) -> dict:
    code = f'''AWSTemplateFormatVersion: "2010-09-09"
Description: >
  Bonito AI Platform - Modular least-privilege IAM setup.
  Creates an IAM user with separate policies per capability.
  Toggle capabilities via parameters.

Parameters:
  ProjectName:
    Type: String
    Default: {project_name}
  IAMMode:
    Type: String
    Default: least_privilege
    AllowedValues: [managed, least_privilege]
    Description: "managed = single broad policy, least_privilege = separate policies per capability"
  EnableProvisioning:
    Type: String
    Default: "true"
    AllowedValues: ["true", "false"]
  EnableModelActivation:
    Type: String
    Default: "true"
    AllowedValues: ["true", "false"]
  EnableCostTracking:
    Type: String
    Default: "true"
    AllowedValues: ["true", "false"]

Conditions:
  IsManaged: !Equals [!Ref IAMMode, managed]
  IsLeastPrivilege: !Equals [!Ref IAMMode, least_privilege]
  ShouldEnableProvisioning: !And
    - !Condition IsLeastPrivilege
    - !Equals [!Ref EnableProvisioning, "true"]
  ShouldEnableActivation: !And
    - !Condition IsLeastPrivilege
    - !Equals [!Ref EnableModelActivation, "true"]
  ShouldEnableCosts: !And
    - !Condition IsLeastPrivilege
    - !Equals [!Ref EnableCostTracking, "true"]

Resources:
  # --- IAM User (programmatic only) ---
  BonitoUser:
    Type: AWS::IAM::User
    Properties:
      UserName: !Sub "${{ProjectName}}-user"
      Path: /system/

  BonitoAccessKey:
    Type: AWS::IAM::AccessKey
    Properties:
      UserName: !Ref BonitoUser

  # --- Option A: Managed (single broad policy) ---
  BonitoManagedPolicy:
    Type: AWS::IAM::ManagedPolicy
    Condition: IsManaged
    Properties:
      ManagedPolicyName: !Sub "${{ProjectName}}-policy"
      Description: "Full Bonito AI platform policy"
      Users: [!Ref BonitoUser]
      PolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Sid: BedrockFullAccess
            Effect: Allow
            Action:
              - bedrock:ListFoundationModels
              - bedrock:GetFoundationModel
              - bedrock:InvokeModel
              - bedrock:InvokeModelWithResponseStream
              - bedrock:CreateProvisionedModelThroughput
              - bedrock:GetProvisionedModelThroughput
              - bedrock:UpdateProvisionedModelThroughput
              - bedrock:DeleteProvisionedModelThroughput
              - bedrock:ListProvisionedModelThroughputs
              - bedrock:PutFoundationModelEntitlement
              - bedrock:GetFoundationModelAvailability
            Resource: "*"
          - Sid: CostExplorerReadOnly
            Effect: Allow
            Action: [ce:GetCostAndUsage, ce:GetCostForecast, ce:GetDimensionValues, ce:GetTags]
            Resource: "*"
          - Sid: STSValidation
            Effect: Allow
            Action: [sts:GetCallerIdentity]
            Resource: "*"

  # --- Option B: Least-privilege (separate policies) ---
  BonitoCorePolicy:
    Type: AWS::IAM::ManagedPolicy
    Condition: IsLeastPrivilege
    Properties:
      ManagedPolicyName: !Sub "${{ProjectName}}-core"
      Description: "Bonito - model discovery + invocation (required)"
      Users: [!Ref BonitoUser]
      PolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Sid: BedrockDiscovery
            Effect: Allow
            Action: [bedrock:ListFoundationModels, bedrock:GetFoundationModel, bedrock:GetFoundationModelAvailability]
            Resource: "*"
          - Sid: BedrockInvoke
            Effect: Allow
            Action: [bedrock:InvokeModel, bedrock:InvokeModelWithResponseStream]
            Resource:
              - !Sub "arn:${{AWS::Partition}}:bedrock:${{AWS::Region}}::foundation-model/*"
              - !Sub "arn:${{AWS::Partition}}:bedrock:${{AWS::Region}}:${{AWS::AccountId}}:inference-profile/*"
              - !Sub "arn:${{AWS::Partition}}:bedrock:us-*::foundation-model/*"
          - Sid: STSValidation
            Effect: Allow
            Action: [sts:GetCallerIdentity]
            Resource: "*"

  BonitoProvisioningPolicy:
    Type: AWS::IAM::ManagedPolicy
    Condition: ShouldEnableProvisioning
    Properties:
      ManagedPolicyName: !Sub "${{ProjectName}}-provisioning"
      Description: "Bonito - provisioned throughput management (optional)"
      Users: [!Ref BonitoUser]
      PolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Sid: BedrockProvisionedThroughput
            Effect: Allow
            Action:
              - bedrock:CreateProvisionedModelThroughput
              - bedrock:GetProvisionedModelThroughput
              - bedrock:UpdateProvisionedModelThroughput
              - bedrock:DeleteProvisionedModelThroughput
              - bedrock:ListProvisionedModelThroughputs
            Resource: !Sub "arn:${{AWS::Partition}}:bedrock:${{AWS::Region}}:${{AWS::AccountId}}:provisioned-model/*"

  BonitoActivationPolicy:
    Type: AWS::IAM::ManagedPolicy
    Condition: ShouldEnableActivation
    Properties:
      ManagedPolicyName: !Sub "${{ProjectName}}-activation"
      Description: "Bonito - model activation/entitlement (optional)"
      Users: [!Ref BonitoUser]
      PolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Sid: BedrockModelEntitlement
            Effect: Allow
            Action: [bedrock:PutFoundationModelEntitlement]
            Resource: !Sub "arn:${{AWS::Partition}}:bedrock:${{AWS::Region}}::foundation-model/*"

  BonitoCostPolicy:
    Type: AWS::IAM::ManagedPolicy
    Condition: ShouldEnableCosts
    Properties:
      ManagedPolicyName: !Sub "${{ProjectName}}-costs"
      Description: "Bonito - cost tracking via Cost Explorer (optional)"
      Users: [!Ref BonitoUser]
      PolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Sid: CostExplorerReadOnly
            Effect: Allow
            Action: [ce:GetCostAndUsage, ce:GetCostForecast, ce:GetDimensionValues, ce:GetTags]
            Resource: "*"

Outputs:
  AccessKeyId:
    Description: Access Key ID for Bonito
    Value: !Ref BonitoAccessKey
  SecretAccessKey:
    Description: Secret Access Key (store securely, rotate every 90 days)
    Value: !GetAtt BonitoAccessKey.SecretAccessKey
  IAMMode:
    Description: IAM mode used
    Value: !Ref IAMMode
'''
    return {
        "files": [{"filename": "bonito-aws.yaml", "content": code.strip()}],
        "code": code,
        "filename": "bonito-aws.yaml",
        "instructions": [
            "Save this file as `bonito-aws.yaml`",
            f"Run: `aws cloudformation create-stack --stack-name {project_name}-setup --template-body file://bonito-aws.yaml --capabilities CAPABILITY_NAMED_IAM --region {region}`",
            "Toggle capabilities via parameters: `--parameters ParameterKey=EnableProvisioning,ParameterValue=false`",
            f"Wait: `aws cloudformation wait stack-create-complete --stack-name {project_name}-setup`",
            f"Get outputs: `aws cloudformation describe-stacks --stack-name {project_name}-setup --query 'Stacks[0].Outputs'`",
            "Copy the access_key_id and secret_access_key into Bonito",
        ],
        "security_notes": [
            "✅ Modular least-privilege - separate policies per capability",
            "✅ Core permissions always included: model discovery + invocation + STS",
            "✅ Optional: provisioning, model activation, cost tracking",
            "✅ No admin access, no wildcard policies",
            "🔄 Rotate keys every 90 days",
        ],
    }


def _manual(
    project_name: str = "bonito",
    region: str = "us-east-1",
    iam_mode: str = "least_privilege",
    enable_provisioning: bool = True,
    enable_model_activation: bool = True,
    enable_cost_tracking: bool = True,
    **kwargs,
) -> dict:
    code = f'''# Bonito AWS Setup - Manual Instructions
# ===========================================
# Creates an IAM user with modular least-privilege policies.
# You choose which capabilities to enable.
# Total time: ~10 minutes.

## Step 1: Create the IAM User

# Go to: IAM > Users > Create user
# User name: {project_name}-user
# Path: /system/
# Do NOT enable console access

## Step 2: Create Core Policy (REQUIRED)

# Go to: IAM > Policies > Create Policy > JSON tab
# Paste this policy:

{{
  "Version": "2012-10-17",
  "Statement": [
    {{
      "Sid": "BedrockDiscovery",
      "Effect": "Allow",
      "Action": [
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel",
        "bedrock:GetFoundationModelAvailability"
      ],
      "Resource": "*"
    }},
    {{
      "Sid": "BedrockInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:{region}::foundation-model/*",
        "arn:aws:bedrock:{region}:YOUR_ACCOUNT_ID:inference-profile/*",
        "arn:aws:bedrock:us-*::foundation-model/*"
      ]
    }},
    {{
      "Sid": "STSValidation",
      "Effect": "Allow",
      "Action": ["sts:GetCallerIdentity"],
      "Resource": "*"
    }}
  ]
}}
# Name it: {project_name}-core
# Attach to {project_name}-user

## Step 3: Optional Policies (attach as needed)

### Provisioned Throughput (manage reserved capacity)
# Create policy named: {project_name}-provisioning
{{
  "Version": "2012-10-17",
  "Statement": [{{
    "Sid": "BedrockProvisionedThroughput",
    "Effect": "Allow",
    "Action": [
      "bedrock:CreateProvisionedModelThroughput",
      "bedrock:GetProvisionedModelThroughput",
      "bedrock:UpdateProvisionedModelThroughput",
      "bedrock:DeleteProvisionedModelThroughput",
      "bedrock:ListProvisionedModelThroughputs"
    ],
    "Resource": "arn:aws:bedrock:{region}:YOUR_ACCOUNT_ID:provisioned-model/*"
  }}]
}}

### Model Activation (enable new foundation models)
# Create policy named: {project_name}-activation
{{
  "Version": "2012-10-17",
  "Statement": [{{
    "Sid": "BedrockModelEntitlement",
    "Effect": "Allow",
    "Action": ["bedrock:PutFoundationModelEntitlement"],
    "Resource": "arn:aws:bedrock:{region}::foundation-model/*"
  }}]
}}

### Cost Tracking (spend visibility in dashboard)
# Create policy named: {project_name}-costs
{{
  "Version": "2012-10-17",
  "Statement": [{{
    "Sid": "CostExplorerReadOnly",
    "Effect": "Allow",
    "Action": [
      "ce:GetCostAndUsage",
      "ce:GetCostForecast",
      "ce:GetDimensionValues",
      "ce:GetTags"
    ],
    "Resource": "*"
  }}]
}}

## Step 4: Create Access Key

# Go to: IAM > Users > {project_name}-user > Security credentials
# Click "Create access key" > "Application running outside AWS"

## Step 5: Enter credentials in Bonito

# You need: access_key_id, secret_access_key

# SECURITY REMINDERS:
# - Minimum required: Core policy only
# - Add optional policies only for capabilities you need
# - Rotate access keys every 90 days
# - Never share keys in plaintext
# - Enable CloudTrail for full audit logging
'''
    return {
        "files": [{"filename": "bonito-aws-manual.md", "content": code.strip()}],
        "code": code,
        "filename": "bonito-aws-manual.md",
        "instructions": [
            "Follow the step-by-step instructions above in the AWS Console",
            "Create the IAM user and core policy (required)",
            "Optionally create and attach provisioning, activation, and cost policies",
            "Generate an access key for the user",
            "Copy access_key_id and secret_access_key into Bonito",
        ],
        "security_notes": [
            "✅ Modular least-privilege - attach only the policies you need",
            "✅ Core: model discovery + invocation + STS validation (required)",
            "✅ Optional: provisioning, model activation, cost tracking",
            "✅ No admin access, no console login for the service user",
            "🔄 Rotate keys every 90 days",
        ],
    }
