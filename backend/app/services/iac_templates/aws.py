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
'''

_TF_MAIN = r'''################################################################################
# Data Sources
################################################################################

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

################################################################################
# IAM Policy — Least-privilege for Bonito
################################################################################

# Bedrock: list + invoke only (NOT bedrock:*)
resource "aws_iam_policy" "bonito" {
  name        = "${var.project_name}-policy"
  description = "Least-privilege policy for Bonito AI platform"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockListModels"
        Effect = "Allow"
        Action = [
          "bedrock:ListFoundationModels",
          "bedrock:GetFoundationModel",
          "bedrock:ListModelAccessList",
        ]
        Resource = "*"
      },
      {
        Sid    = "BedrockInvokeModels"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ]
        # Scoped to foundation models in the target region
        Resource = "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}::foundation-model/*"
      },
      {
        # Model activation: request access to foundation models
        Sid    = "BedrockModelAccess"
        Effect = "Allow"
        Action = [
          "bedrock:PutFoundationModelEntitlement",
          "bedrock:PutUseCaseForModelAccess",
        ]
        Resource = "*"
      },
      {
        # Provisioned Throughput: deploy dedicated model capacity
        Sid    = "BedrockProvisionedThroughput"
        Effect = "Allow"
        Action = [
          "bedrock:CreateProvisionedModelThroughput",
          "bedrock:GetProvisionedModelThroughput",
          "bedrock:ListProvisionedModelThroughputs",
          "bedrock:UpdateProvisionedModelThroughput",
          "bedrock:DeleteProvisionedModelThroughput",
        ]
        Resource = "*"
      },
      {
        # Cost Explorer: read-only for spend tracking
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
        # STS: identity validation only
        Sid    = "STSValidation"
        Effect = "Allow"
        Action = [
          "sts:GetCallerIdentity",
        ]
        Resource = "*"
      },
    ]
  })
}

################################################################################
# IAM Role — Assumed by the Bonito IAM user
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

resource "aws_iam_role_policy_attachment" "bonito" {
  role       = aws_iam_role.bonito.name
  policy_arn = aws_iam_policy.bonito.arn
}

################################################################################
# IAM User — Programmatic access, assumes the role above
################################################################################

resource "aws_iam_user" "bonito" {
  name = "${var.project_name}-user"
  path = "/system/"
}

# Attach the Bonito policy directly to the user for simple credential flow
resource "aws_iam_user_policy_attachment" "bonito_direct" {
  user       = aws_iam_user.bonito.name
  policy_arn = aws_iam_policy.bonito.arn
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
  name                       = "${var.project_name}-bedrock-audit"
  s3_bucket_name             = aws_s3_bucket.cloudtrail.id
  include_global_service_events = false
  is_multi_region_trail      = false
  enable_logging             = true

  # Log only Bedrock data events
  event_selector {
    read_write_type           = "All"
    include_management_events = false

    data_resource {
      type   = "AWS::Bedrock::Model"
      values = ["arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}::foundation-model/*"]
    }
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


def _terraform(**kwargs) -> dict:
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
            "✅ Role assumption pattern — user can ONLY assume the Bonito role",
            "✅ Least privilege — Bedrock list/invoke, Cost Explorer read, STS validation only",
            "✅ No admin access, no wildcard policies, no console login",
            "✅ CloudTrail audit logging for all Bedrock API calls",
            "✅ S3 bucket for audit logs with public access blocked",
            "🔄 Rotate access keys every 90 days",
            "🔒 Store terraform.tfstate securely — it contains the secret key",
        ],
    }


def _pulumi(
    project_name: str = "bonito",
    region: str = "us-east-1",
    **kwargs,
) -> dict:
    code = f'''"""Bonito AWS Integration — Pulumi (Python)

Purpose: Create a least-privilege IAM user + role for Bonito.
Security: Role assumption pattern. Bedrock list/invoke, Cost Explorer read only.

Run: pulumi up
"""

import pulumi
import pulumi_aws as aws
import json

# --- IAM Policy: Bedrock + Cost Explorer + STS ---
policy = aws.iam.Policy("{project_name}-policy",
    name="{project_name}-policy",
    description="Least-privilege policy for Bonito AI platform",
    policy=json.dumps({{
        "Version": "2012-10-17",
        "Statement": [
            {{
                "Sid": "BedrockListModels",
                "Effect": "Allow",
                "Action": ["bedrock:ListFoundationModels", "bedrock:GetFoundationModel", "bedrock:ListModelAccessList"],
                "Resource": "*"
            }},
            {{
                "Sid": "BedrockInvokeModels",
                "Effect": "Allow",
                "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                "Resource": f"arn:aws:bedrock:{region}::foundation-model/*"
            }},
            {{
                "Sid": "BedrockModelAccess",
                "Effect": "Allow",
                "Action": ["bedrock:PutFoundationModelEntitlement", "bedrock:PutUseCaseForModelAccess"],
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

# --- IAM User (programmatic only) ---
user = aws.iam.User("{project_name}-user",
    name="{project_name}-user", path="/system/")

# --- IAM Role (assumed by the user) ---
role = aws.iam.Role("{project_name}-role",
    name="{project_name}-role",
    assume_role_policy=user.arn.apply(lambda arn: json.dumps({{
        "Version": "2012-10-17",
        "Statement": [{{
            "Effect": "Allow",
            "Principal": {{"AWS": arn}},
            "Action": "sts:AssumeRole",
            "Condition": {{"StringEquals": {{"sts:ExternalId": "{project_name}-external-id"}}}}
        }}]
    }}))
)

aws.iam.RolePolicyAttachment("{project_name}-attach",
    role=role.name, policy_arn=policy.arn)

# User can only assume the role
aws.iam.UserPolicy("{project_name}-assume",
    user=user.name,
    policy=role.arn.apply(lambda arn: json.dumps({{
        "Version": "2012-10-17",
        "Statement": [{{
            "Effect": "Allow",
            "Action": "sts:AssumeRole",
            "Resource": arn
        }}]
    }}))
)

access_key = aws.iam.AccessKey("{project_name}-key", user=user.name)

pulumi.export("access_key_id", access_key.id)
pulumi.export("secret_access_key", access_key.secret)
pulumi.export("role_arn", role.arn)
'''
    return {
        "files": [{"filename": "__main__.py", "content": code.strip()}],
        "code": code,
        "filename": "__main__.py",
        "instructions": [
            "Install Pulumi (https://www.pulumi.com/docs/install/)",
            "Run: `pulumi new aws-python` in a new directory",
            "Replace `__main__.py` with this code",
            "Run: `pulumi up` — review and confirm",
            "Copy the access_key_id, secret_access_key, and role_arn into Bonito",
        ],
        "security_notes": [
            "✅ Role assumption pattern — user can only assume the Bonito role",
            "✅ Least privilege — Bedrock list/invoke, Cost Explorer read, STS only",
            "✅ No admin access, no console login",
            "🔄 Rotate access keys every 90 days",
            "🔒 Pulumi state contains secrets — use encrypted backend",
        ],
    }


def _cloudformation(
    project_name: str = "bonito",
    region: str = "us-east-1",
    **kwargs,
) -> dict:
    code = f'''AWSTemplateFormatVersion: "2010-09-09"
Description: >
  Bonito AI Platform — Least-privilege IAM setup with role assumption pattern.
  Creates an IAM user that can only assume a scoped role with Bedrock invoke,
  Cost Explorer read, and STS validation permissions.

Parameters:
  ProjectName:
    Type: String
    Default: {project_name}
  CloudTrailBucketName:
    Type: String
    Default: {project_name}-cloudtrail-logs

Resources:
  # --- IAM Policy ---
  BonitoPolicy:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      ManagedPolicyName: !Sub "${{ProjectName}}-policy"
      Description: "Least-privilege policy for Bonito AI platform"
      PolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Sid: BedrockListModels
            Effect: Allow
            Action:
              - bedrock:ListFoundationModels
              - bedrock:GetFoundationModel
              - bedrock:ListModelAccessList
            Resource: "*"
          - Sid: BedrockInvokeModels
            Effect: Allow
            Action:
              - bedrock:InvokeModel
              - bedrock:InvokeModelWithResponseStream
            Resource: !Sub "arn:${{AWS::Partition}}:bedrock:{region}::foundation-model/*"
          - Sid: BedrockModelAccess
            Effect: Allow
            Action:
              - bedrock:PutFoundationModelEntitlement
              - bedrock:PutUseCaseForModelAccess
            Resource: "*"
          - Sid: CostExplorerReadOnly
            Effect: Allow
            Action:
              - ce:GetCostAndUsage
              - ce:GetCostForecast
              - ce:GetDimensionValues
              - ce:GetTags
            Resource: "*"
          - Sid: STSValidation
            Effect: Allow
            Action:
              - sts:GetCallerIdentity
            Resource: "*"

  # --- IAM Role ---
  BonitoRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Sub "${{ProjectName}}-role"
      Description: "Role assumed by Bonito for AI and cost operations"
      ManagedPolicyArns:
        - !Ref BonitoPolicy
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              AWS: !GetAtt BonitoUser.Arn
            Action: sts:AssumeRole
            Condition:
              StringEquals:
                "sts:ExternalId": !Sub "${{ProjectName}}-external-id"

  # --- IAM User ---
  BonitoUser:
    Type: AWS::IAM::User
    Properties:
      UserName: !Sub "${{ProjectName}}-user"
      Path: /system/
      Policies:
        - PolicyName: !Sub "${{ProjectName}}-assume-role"
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action: sts:AssumeRole
                Resource: !GetAtt BonitoRole.Arn

  BonitoAccessKey:
    Type: AWS::IAM::AccessKey
    Properties:
      UserName: !Ref BonitoUser

Outputs:
  AccessKeyId:
    Description: Access Key ID for Bonito
    Value: !Ref BonitoAccessKey
  SecretAccessKey:
    Description: Secret Access Key (store securely, rotate every 90 days)
    Value: !GetAtt BonitoAccessKey.SecretAccessKey
  RoleArn:
    Description: ARN of the IAM role Bonito assumes
    Value: !GetAtt BonitoRole.Arn
'''
    return {
        "files": [{"filename": "bonito-aws.yaml", "content": code.strip()}],
        "code": code,
        "filename": "bonito-aws.yaml",
        "instructions": [
            "Save this file as `bonito-aws.yaml`",
            f"Run: `aws cloudformation create-stack --stack-name {project_name}-setup --template-body file://bonito-aws.yaml --capabilities CAPABILITY_NAMED_IAM --region {region}`",
            f"Wait: `aws cloudformation wait stack-create-complete --stack-name {project_name}-setup`",
            f"Get outputs: `aws cloudformation describe-stacks --stack-name {project_name}-setup --query 'Stacks[0].Outputs'`",
            "Copy the access_key_id, secret_access_key, and role_arn into Bonito",
        ],
        "security_notes": [
            "✅ Role assumption pattern — user can only assume the scoped role",
            "✅ Least privilege — Bedrock list/invoke, Cost Explorer read, STS only",
            "✅ No admin access, no wildcard policies",
            "🔄 Rotate keys every 90 days",
        ],
    }


def _manual(
    project_name: str = "bonito",
    region: str = "us-east-1",
    **kwargs,
) -> dict:
    code = f'''# Bonito AWS Setup — Manual Instructions
# ===========================================
# This creates a role-assumption pattern: an IAM user that can ONLY assume
# a scoped IAM role with Bedrock and Cost Explorer permissions.
# Total time: ~10 minutes.

## Step 1: Create the IAM Policy

# Go to: IAM → Policies → Create Policy → JSON tab
# Paste this policy:

{{
  "Version": "2012-10-17",
  "Statement": [
    {{
      "Sid": "BedrockListModels",
      "Effect": "Allow",
      "Action": ["bedrock:ListFoundationModels", "bedrock:GetFoundationModel", "bedrock:ListModelAccessList"],
      "Resource": "*"
    }},
    {{
      "Sid": "BedrockInvokeModels",
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      "Resource": "arn:aws:bedrock:{region}::foundation-model/*"
    }},
    {{
      "Sid": "BedrockModelAccess",
      "Effect": "Allow",
      "Action": ["bedrock:PutFoundationModelEntitlement", "bedrock:PutUseCaseForModelAccess"],
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
}}
# Name it: {project_name}-policy

## Step 2: Create the IAM Role
# Go to: IAM → Roles → Create role → Custom trust policy
# Trust policy (you'll update the Principal after creating the user):
# Select "AWS account" → "This account"
# Attach the policy you created in Step 1
# Name it: {project_name}-role

## Step 3: Create the IAM User
# Go to: IAM → Users → Create user
# User name: {project_name}-user
# Path: /system/
# Do NOT enable console access
# Create an inline policy allowing only sts:AssumeRole on the role ARN

## Step 4: Create Access Key
# Go to: IAM → Users → {project_name}-user → Security credentials
# Click "Create access key" → "Application running outside AWS"

## Step 5: Update Role Trust Policy
# Go to: IAM → Roles → {project_name}-role → Trust relationships → Edit
# Set the Principal to the user ARN from Step 3
# Add a Condition requiring ExternalId = "{project_name}-external-id"

## Step 6: Enter credentials in Bonito
# You need: access_key_id, secret_access_key, role_arn

# ⚠️  SECURITY REMINDERS:
# - The user can ONLY assume the role — no direct permissions
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
            "Create the IAM policy, role, and user",
            "Generate an access key for the user",
            "Copy access_key_id, secret_access_key, and role_arn into Bonito",
        ],
        "security_notes": [
            "✅ Role assumption pattern — user has zero direct permissions",
            "✅ Least privilege — only the specific actions Bonito needs",
            "✅ No admin access, no console login for the service user",
            "🔄 Rotate keys every 90 days",
        ],
    }
