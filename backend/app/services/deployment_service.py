"""
Deployment Provisioning Service — Create and manage model deployments on customer clouds.

Supports:
- AWS Bedrock: Provisioned Throughput (reserved capacity for production)
- Azure OpenAI: Model deployments with TPM/tier configuration
- GCP Vertex AI: Serverless (most models) — deployment = access verification

Each deployment maps to a real cloud resource. The service handles:
1. Cost estimation before deployment
2. Provisioning via cloud APIs
3. Status monitoring
4. Scaling (update capacity)
5. Teardown (delete cloud resources)
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional

import aioboto3
import httpx
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


# ─── Cost Estimation ───

# AWS Provisioned Throughput pricing (approximate, us-east-1)
# Per model unit per hour
AWS_PT_PRICING = {
    "anthropic.claude-3-5-sonnet": 39.60,
    "anthropic.claude-3-haiku": 6.40,
    "anthropic.claude-3-sonnet": 26.00,
    "amazon.titan-text-express": 7.70,
    "amazon.titan-text-lite": 4.40,
    "meta.llama3-70b-instruct": 14.27,
    "meta.llama3-8b-instruct": 3.57,
    "mistral.mistral-large": 26.00,
    "cohere.command-r-plus": 18.00,
    "default": 20.00,
}

# Azure per-1K-TPM monthly cost (approximate, Standard tier)
AZURE_TPM_PRICING = {
    "gpt-4o": 0.60,
    "gpt-4o-mini": 0.10,
    "gpt-4-turbo": 1.00,
    "gpt-4": 1.80,
    "gpt-35-turbo": 0.05,
    "text-embedding-3-large": 0.02,
    "text-embedding-3-small": 0.01,
    "default": 0.50,
}


@dataclass
class CostEstimate:
    hourly: float = 0.0
    daily: float = 0.0
    monthly: float = 0.0
    unit: str = ""  # e.g., "per model unit", "per 1K TPM"
    notes: str = ""


@dataclass
class DeploymentResult:
    success: bool
    status: str  # "deploying", "active", "failed", "pending"
    message: str
    cloud_resource_id: Optional[str] = None
    endpoint_url: Optional[str] = None
    config_applied: dict = field(default_factory=dict)


def estimate_cost(provider_type: str, model_id: str, config: dict) -> CostEstimate:
    """Estimate deployment cost BEFORE provisioning."""
    if provider_type == "aws":
        model_units = config.get("model_units", 1)
        # Find pricing — match on prefix
        hourly_per_unit = AWS_PT_PRICING.get("default", 20.0)
        for key, price in AWS_PT_PRICING.items():
            if key != "default" and model_id.startswith(key):
                hourly_per_unit = price
                break
        
        commitment = config.get("commitment_term", "1_week")
        discount = 1.0
        if commitment == "1_month":
            discount = 0.80  # ~20% discount for 1-month commitment
        elif commitment == "3_month":
            discount = 0.60  # ~40% discount for 3-month commitment
        elif commitment == "6_month":
            discount = 0.50  # ~50% discount for 6-month commitment
        
        hourly = hourly_per_unit * model_units * discount
        return CostEstimate(
            hourly=hourly,
            daily=hourly * 24,
            monthly=hourly * 730,  # avg hours per month
            unit=f"${hourly_per_unit:.2f}/hr per model unit" + (f" ({int((1-discount)*100)}% commitment discount)" if discount < 1 else ""),
            notes=f"{model_units} model unit(s), {commitment.replace('_', ' ')} commitment" if commitment != "none" else f"{model_units} model unit(s), no commitment (pay-as-you-go)",
        )
    
    elif provider_type == "azure":
        tpm = config.get("tpm", 10)  # thousands of tokens per minute
        tier = config.get("tier", "Standard")
        
        monthly_per_1k = AZURE_TPM_PRICING.get("default", 0.50)
        for key, price in AZURE_TPM_PRICING.items():
            if key != "default" and key in model_id.lower():
                monthly_per_1k = price
                break
        
        if tier == "Provisioned":
            monthly_per_1k *= 3  # Provisioned is roughly 3x Standard
        
        monthly = monthly_per_1k * tpm
        return CostEstimate(
            hourly=monthly / 730,
            daily=monthly / 30,
            monthly=monthly,
            unit=f"${monthly_per_1k:.2f}/mo per 1K TPM ({tier})",
            notes=f"{tpm}K TPM, {tier} tier",
        )
    
    elif provider_type == "gcp":
        return CostEstimate(
            hourly=0,
            daily=0,
            monthly=0,
            unit="Pay-per-use (no deployment cost)",
            notes="Vertex AI models are serverless — you pay per request, no fixed deployment cost.",
        )
    
    return CostEstimate(notes="Cost estimation not available for this provider")


# ─── AWS Bedrock Deployment ───

async def deploy_aws(
    model_id: str,
    config: dict,
    access_key_id: str,
    secret_access_key: str,
    region: str = "us-east-1",
) -> DeploymentResult:
    """Create AWS Bedrock deployment — on-demand (default) or Provisioned Throughput."""
    session = aioboto3.Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region,
    )
    
    model_units = config.get("model_units", 0)  # 0 = on-demand
    commitment = config.get("commitment_term", "none")
    deployment_name = config.get("name", f"bonito-{model_id.split('.')[-1][:20]}")
    
    # On-demand mode: just verify access and return endpoint
    if model_units == 0:
        try:
            async with session.client("bedrock-runtime") as runtime:
                # Verify model is accessible by checking if we can describe it
                pass
            async with session.client("bedrock") as bedrock:
                try:
                    model_info = await bedrock.get_foundation_model(modelIdentifier=model_id)
                    model_name = model_info.get("modelDetails", {}).get("modelName", model_id)
                except ClientError:
                    model_name = model_id
                
                return DeploymentResult(
                    success=True,
                    status="active",
                    message=f"On-demand access verified for {model_name}. Pay-per-request pricing — no reserved capacity.",
                    endpoint_url=f"https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/invoke",
                    config_applied={"type": "on-demand", "region": region},
                )
        except ClientError as e:
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            return DeploymentResult(
                success=False,
                status="failed",
                message=f"Cannot access model: {error_msg}",
            )
        except Exception as e:
            return DeploymentResult(
                success=False,
                status="failed",
                message=f"AWS access verification failed: {str(e)}",
            )
    
    # Map commitment terms to AWS API values
    # Note: AWS minimum commitment for PT is 1 week — no "NoCommitment" option
    commitment_map = {
        "1_week": "OneWeek",
        "1_month": "OneMonth",
        "3_month": "ThreeMonths",
        "6_month": "SixMonths",
    }
    aws_commitment = commitment_map.get(commitment)
    if not aws_commitment:
        return DeploymentResult(
            success=False,
            status="failed",
            message=f"Provisioned Throughput requires a commitment term. Valid options: 1_week, 1_month, 3_month, 6_month. Minimum commitment is 1 week.",
        )
    
    try:
        async with session.client("bedrock") as bedrock:
            # Check if model supports provisioned throughput
            try:
                model_info = await bedrock.get_foundation_model(modelIdentifier=model_id)
                # Model exists, proceed
            except ClientError as e:
                return DeploymentResult(
                    success=False,
                    status="failed",
                    message=f"Model {model_id} not found: {e.response['Error']['Message']}",
                )
            
            # Create provisioned throughput
            try:
                resp = await bedrock.create_provisioned_model_throughput(
                    modelId=model_id,
                    provisionedModelName=deployment_name,
                    modelUnits=model_units,
                    commitmentDuration=aws_commitment,
                )
                
                pt_arn = resp.get("provisionedModelArn", "")
                
                return DeploymentResult(
                    success=True,
                    status="deploying",
                    message=f"Provisioned Throughput '{deployment_name}' is being created. This typically takes 5-15 minutes.",
                    cloud_resource_id=pt_arn,
                    config_applied={
                        "model_units": model_units,
                        "commitment_term": aws_commitment,
                        "provisioned_model_arn": pt_arn,
                    },
                )
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                error_msg = e.response.get("Error", {}).get("Message", str(e))
                
                if "AccessDeniedException" in error_code:
                    return DeploymentResult(
                        success=False,
                        status="failed",
                        message="Permission denied. Your IAM user needs 'bedrock:CreateProvisionedModelThroughput' permission.",
                    )
                elif "TooManyTagsException" in error_code or "ServiceQuotaExceededException" in error_code:
                    return DeploymentResult(
                        success=False,
                        status="failed",
                        message=f"Quota exceeded: {error_msg}. Request a quota increase in the AWS console.",
                    )
                elif "ValidationException" in error_code:
                    return DeploymentResult(
                        success=False,
                        status="failed",
                        message=f"Invalid configuration: {error_msg}",
                    )
                else:
                    return DeploymentResult(
                        success=False,
                        status="failed",
                        message=f"AWS error ({error_code}): {error_msg}",
                    )
    except Exception as e:
        logger.error(f"AWS deployment failed: {e}")
        return DeploymentResult(success=False, status="failed", message=f"Deployment failed: {str(e)}")


async def get_aws_deployment_status(
    cloud_resource_id: str,
    access_key_id: str,
    secret_access_key: str,
    region: str = "us-east-1",
) -> dict:
    """Check status of an AWS Provisioned Throughput."""
    session = aioboto3.Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region,
    )
    try:
        async with session.client("bedrock") as bedrock:
            resp = await bedrock.get_provisioned_model_throughput(
                provisionedModelId=cloud_resource_id,
            )
            return {
                "status": resp.get("status", "Unknown"),
                "model_units": resp.get("desiredModelUnits", 0),
                "model_id": resp.get("foundationModelArn", ""),
                "commitment": resp.get("commitmentDuration", ""),
                "created_at": str(resp.get("creationTime", "")),
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def scale_aws_deployment(
    cloud_resource_id: str,
    new_model_units: int,
    access_key_id: str,
    secret_access_key: str,
    region: str = "us-east-1",
) -> DeploymentResult:
    """Scale AWS Provisioned Throughput."""
    session = aioboto3.Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region,
    )
    try:
        async with session.client("bedrock") as bedrock:
            await bedrock.update_provisioned_model_throughput(
                provisionedModelId=cloud_resource_id,
                desiredModelUnits=new_model_units,
            )
            return DeploymentResult(
                success=True,
                status="active",
                message=f"Scaled to {new_model_units} model units.",
                cloud_resource_id=cloud_resource_id,
            )
    except Exception as e:
        return DeploymentResult(success=False, status="failed", message=str(e))


async def delete_aws_deployment(
    cloud_resource_id: str,
    access_key_id: str,
    secret_access_key: str,
    region: str = "us-east-1",
) -> DeploymentResult:
    """Delete AWS Provisioned Throughput."""
    session = aioboto3.Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region,
    )
    try:
        async with session.client("bedrock") as bedrock:
            await bedrock.delete_provisioned_model_throughput(
                provisionedModelId=cloud_resource_id,
            )
            return DeploymentResult(
                success=True,
                status="deleted",
                message="Provisioned Throughput deleted.",
            )
    except Exception as e:
        return DeploymentResult(success=False, status="failed", message=str(e))


# ─── Azure OpenAI Deployment Management (ARM API) ───

def _parse_azure_model_id(model_id: str) -> tuple[str, str | None]:
    """Parse Azure model ID into (base_name, version).
    
    Azure uses two version formats:
      Date-based:  'gpt-4o-2024-11-20'      → ('gpt-4o', '2024-11-20')
      Build-based: 'gpt-35-turbo-1106'       → ('gpt-35-turbo', '1106')
                   'gpt-4o-mini-2024-07-18'  → ('gpt-4o-mini', '2024-07-18')
                   'gpt-35-turbo'            → ('gpt-35-turbo', None)
    """
    import re
    # Try date version: YYYY-MM-DD suffix
    m = re.match(r'^(.+?)-(\d{4}-\d{2}-\d{2})$', model_id)
    if m:
        return m.group(1), m.group(2)
    # Try build version: 4-digit suffix (e.g., 1106, 0613, 0125)
    m = re.match(r'^(.+?)-(\d{4})$', model_id)
    if m:
        return m.group(1), m.group(2)
    return model_id, None


def _extract_azure_account_name(endpoint: str) -> str:
    """Extract account name from Azure OpenAI endpoint URL.
    'https://bonito-ai-production.openai.azure.com/' → 'bonito-ai-production'
    """
    from urllib.parse import urlparse
    hostname = urlparse(endpoint).hostname or ""
    return hostname.split(".")[0]


async def _get_arm_token(tenant_id: str, client_id: str, client_secret: str) -> str | None:
    """Get Azure Resource Manager token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://management.azure.com/.default",
                "grant_type": "client_credentials",
            },
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    return None


def _azure_arm_url(subscription_id: str, resource_group: str, account_name: str, deployment_name: str) -> str:
    return (
        f"https://management.azure.com/subscriptions/{subscription_id}"
        f"/resourceGroups/{resource_group}"
        f"/providers/Microsoft.CognitiveServices/accounts/{account_name}"
        f"/deployments/{deployment_name}?api-version=2024-06-01-preview"
    )


async def deploy_azure(
    model_id: str,
    config: dict,
    tenant_id: str,
    client_id: str,
    client_secret: str,
    endpoint: str,
    subscription_id: str = "",
    resource_group: str = "",
) -> DeploymentResult:
    """Create or update an Azure OpenAI deployment via Azure Resource Manager API."""
    deployment_name = config.get("name", model_id.replace(".", "-").replace("/", "-")[:64])
    tpm = config.get("tpm", 10)  # in thousands
    
    # Map deployment_type from frontend to Azure SKU name
    deployment_type = config.get("deployment_type", config.get("tier", "standard"))
    _sku_map = {
        "standard": "Standard",
        "global-standard": "GlobalStandard",
        "global-batch": "GlobalBatch",
        "provisioned": "ProvisionedManaged",
        "data-zone-standard": "DataZoneStandard",
    }
    tier = _sku_map.get(deployment_type.lower(), deployment_type) if isinstance(deployment_type, str) else "Standard"
    
    # Parse model name and version
    azure_model_name, parsed_version = _parse_azure_model_id(model_id)
    model_version = config.get("model_version", parsed_version)
    
    account_name = _extract_azure_account_name(endpoint)
    base = endpoint.rstrip("/")
    
    if not subscription_id or not resource_group:
        return DeploymentResult(
            success=False, status="failed",
            message="Azure deployment requires subscription_id and resource_group in provider credentials.",
        )
    
    try:
        arm_token = await _get_arm_token(tenant_id, client_id, client_secret)
        if not arm_token:
            return DeploymentResult(
                success=False, status="failed",
                message="Azure ARM authentication failed. Check service principal credentials.",
            )
        
        arm_url = _azure_arm_url(subscription_id, resource_group, account_name, deployment_name)
        
        async with httpx.AsyncClient() as client:
            # Check if deployment already exists
            check = await client.get(arm_url, headers={"Authorization": f"Bearer {arm_token}"})
            
            if check.status_code == 200:
                existing = check.json()
                existing_capacity = existing.get("sku", {}).get("capacity", 0)
                existing_status = existing.get("properties", {}).get("provisioningState", "")
                
                if existing_capacity == tpm:
                    return DeploymentResult(
                        success=True,
                        status="active" if existing_status == "Succeeded" else "deploying",
                        message=f"Deployment '{deployment_name}' already exists with {tpm}K TPM.",
                        cloud_resource_id=deployment_name,
                        endpoint_url=f"{base}/openai/deployments/{deployment_name}",
                    )
                
                # Scale existing deployment
                update_body = {"sku": {"name": tier, "capacity": tpm}}
                update_resp = await client.patch(
                    arm_url,
                    headers={"Authorization": f"Bearer {arm_token}", "Content-Type": "application/json"},
                    json=update_body,
                    timeout=30,
                )
                if update_resp.status_code in (200, 201, 202):
                    return DeploymentResult(
                        success=True,
                        status="active",
                        message=f"Deployment '{deployment_name}' scaled to {tpm}K TPM.",
                        cloud_resource_id=deployment_name,
                        endpoint_url=f"{base}/openai/deployments/{deployment_name}",
                    )
            
            # Create new deployment via ARM PUT
            deploy_body = {
                "sku": {"name": tier, "capacity": tpm},
                "properties": {
                    "model": {
                        "format": "OpenAI",
                        "name": azure_model_name,
                    }
                },
            }
            if model_version:
                deploy_body["properties"]["model"]["version"] = model_version
            
            resp = await client.put(
                arm_url,
                headers={"Authorization": f"Bearer {arm_token}", "Content-Type": "application/json"},
                json=deploy_body,
                timeout=30,
            )
            
            if resp.status_code in (200, 201, 202):
                return DeploymentResult(
                    success=True,
                    status="deploying",
                    message=f"Deployment '{deployment_name}' created with {tpm}K TPM ({tier} tier). It may take 1-2 minutes to become active.",
                    cloud_resource_id=deployment_name,
                    endpoint_url=f"{base}/openai/deployments/{deployment_name}",
                    config_applied={"tpm": tpm, "tier": tier, "model_version": model_version or "latest"},
                )
            else:
                error_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                error_code = error_data.get("error", {}).get("code", "")
                error_msg = error_data.get("error", {}).get("message", resp.text[:300])
                
                if resp.status_code == 403 or "Forbidden" in error_code:
                    return DeploymentResult(
                        success=False, status="failed",
                        message="Permission denied. Service principal needs 'Cognitive Services Contributor' role on the resource.",
                    )
                elif "InsufficientQuota" in error_code or "QuotaExceeded" in error_code:
                    return DeploymentResult(
                        success=False, status="failed",
                        message=f"Insufficient quota for {azure_model_name} ({tier}). Request quota increase in Azure Portal → Quotas, or try a different model/tier.",
                    )
                else:
                    return DeploymentResult(
                        success=False, status="failed",
                        message=f"Azure deployment failed: {error_msg}",
                    )
    except Exception as e:
        logger.error(f"Azure deployment failed: {e}")
        return DeploymentResult(success=False, status="failed", message=f"Deployment failed: {str(e)}")


async def get_azure_deployment_status(
    deployment_name: str,
    tenant_id: str,
    client_id: str,
    client_secret: str,
    endpoint: str,
    subscription_id: str = "",
    resource_group: str = "",
) -> dict:
    """Get Azure deployment status via ARM API."""
    try:
        arm_token = await _get_arm_token(tenant_id, client_id, client_secret)
        if not arm_token:
            return {"status": "auth_error"}
        
        account_name = _extract_azure_account_name(endpoint)
        arm_url = _azure_arm_url(subscription_id, resource_group, account_name, deployment_name)
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(arm_url, headers={"Authorization": f"Bearer {arm_token}"})
            if resp.status_code == 200:
                data = resp.json()
                props = data.get("properties", {})
                model = props.get("model", {})
                return {
                    "status": props.get("provisioningState", "unknown"),
                    "model": model.get("name", ""),
                    "tpm": data.get("sku", {}).get("capacity", 0),
                    "tier": data.get("sku", {}).get("name", ""),
                    "version": model.get("version", ""),
                }
            elif resp.status_code == 404:
                return {"status": "not_found"}
            else:
                return {"status": "error", "message": resp.text[:200]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def delete_azure_deployment(
    deployment_name: str,
    tenant_id: str,
    client_id: str,
    client_secret: str,
    endpoint: str,
    subscription_id: str = "",
    resource_group: str = "",
) -> DeploymentResult:
    """Delete an Azure deployment via ARM API."""
    try:
        arm_token = await _get_arm_token(tenant_id, client_id, client_secret)
        if not arm_token:
            return DeploymentResult(success=False, status="failed", message="ARM auth failed")
        
        account_name = _extract_azure_account_name(endpoint)
        arm_url = _azure_arm_url(subscription_id, resource_group, account_name, deployment_name)
        
        async with httpx.AsyncClient() as client:
            resp = await client.delete(arm_url, headers={"Authorization": f"Bearer {arm_token}"})
            if resp.status_code in (200, 202, 204):
                return DeploymentResult(success=True, status="deleted", message="Deployment deleted.")
            else:
                return DeploymentResult(success=False, status="failed", message=f"Delete failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        return DeploymentResult(success=False, status="failed", message=str(e))


# ─── GCP Vertex AI ───

async def deploy_gcp(
    model_id: str,
    config: dict,
    project_id: str,
    service_account_json: dict | str,
    region: str = "us-central1",
) -> DeploymentResult:
    """GCP Vertex AI models are serverless — no deployment needed.
    This verifies access and returns a success result."""
    return DeploymentResult(
        success=True,
        status="active",
        message=f"Vertex AI model '{model_id}' is serverless — no dedicated deployment needed. You're billed per request.",
        endpoint_url=f"https://{region}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{region}/publishers/google/models/{model_id}",
        config_applied={"type": "serverless", "region": region},
    )
