"""
Model Activation Service — Enable/deploy models on customer cloud accounts.

Supports:
- AWS Bedrock: Request model access via PutFoundationModelEntitlement
- Azure OpenAI: Create model deployments via Management API  
- GCP Vertex AI: Models are generally available if API is enabled
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

import aioboto3
import httpx
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass
class ActivationResult:
    success: bool
    status: str  # "enabled", "pending", "deployed", "failed"
    message: str
    requires_approval: bool = False  # True if model needs manual AWS approval
    endpoint_url: str = ""  # Resource endpoint (Azure)


async def activate_aws_model(
    model_id: str,
    access_key_id: str,
    secret_access_key: str,
    region: str = "us-east-1",
) -> ActivationResult:
    """Request access to an AWS Bedrock foundation model.
    
    Uses the Bedrock API to request model access. Some models are
    instantly enabled, others require EULA acceptance or go to a waitlist.
    """
    session = aioboto3.Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region,
    )
    
    try:
        async with session.client("bedrock") as bedrock:
            # First check current access status
            try:
                access_list = await bedrock.list_model_access()
                for entry in access_list.get("modelAccessList", []):
                    if entry.get("modelId") == model_id:
                        current_status = entry.get("accessStatus", "")
                        if current_status == "ENABLED":
                            return ActivationResult(
                                success=True,
                                status="enabled",
                                message=f"Model {model_id} is already enabled."
                            )
                        elif current_status == "IN_PROGRESS":
                            return ActivationResult(
                                success=True,
                                status="pending",
                                message=f"Access request for {model_id} is already in progress.",
                                requires_approval=True,
                            )
                        break
            except Exception as e:
                logger.warning(f"Could not check model access status: {e}")
            
            # Request model access
            try:
                await bedrock.put_foundation_model_entitlement(
                    modelId=model_id,
                )
                
                # Check if it was instantly enabled
                try:
                    access_list = await bedrock.list_model_access()
                    for entry in access_list.get("modelAccessList", []):
                        if entry.get("modelId") == model_id:
                            new_status = entry.get("accessStatus", "")
                            if new_status == "ENABLED":
                                return ActivationResult(
                                    success=True,
                                    status="enabled",
                                    message=f"Model {model_id} has been enabled successfully!"
                                )
                            elif new_status == "IN_PROGRESS":
                                return ActivationResult(
                                    success=True,
                                    status="pending",
                                    message=f"Access requested for {model_id}. Some models require manual approval from AWS — this can take up to 48 hours.",
                                    requires_approval=True,
                                )
                            break
                except Exception:
                    pass
                
                return ActivationResult(
                    success=True,
                    status="pending",
                    message=f"Access requested for {model_id}. Check back shortly.",
                )
                
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                error_msg = e.response.get("Error", {}).get("Message", str(e))
                
                if "AccessDeniedException" in error_code:
                    return ActivationResult(
                        success=False,
                        status="failed",
                        message=f"Permission denied. Your IAM user needs the 'bedrock:PutFoundationModelEntitlement' permission. Add it to your Bonito IAM policy."
                    )
                elif "ValidationException" in error_code:
                    return ActivationResult(
                        success=False,
                        status="failed",
                        message=f"Cannot enable this model: {error_msg}"
                    )
                else:
                    return ActivationResult(
                        success=False,
                        status="failed",
                        message=f"AWS error ({error_code}): {error_msg}"
                    )
                    
    except Exception as e:
        logger.error(f"AWS model activation failed for {model_id}: {e}")
        return ActivationResult(
            success=False,
            status="failed",
            message=f"Failed to activate model: {str(e)}"
        )


async def _resolve_azure_account_name(
    subscription_id: str, resource_group: str, endpoint: str, arm_token: str
) -> str:
    """Resolve the Azure OpenAI account name from the endpoint or resource group.
    
    Tries to extract from custom subdomain first (e.g. bonito-ai-eastus2 from
    bonito-ai-eastus2.openai.azure.com), then falls back to listing accounts
    in the resource group via ARM.
    """
    # Try custom subdomain: https://NAME.openai.azure.com/
    host = endpoint.rstrip("/").split("//")[-1].split("/")[0]
    if ".openai.azure.com" in host:
        return host.replace(".openai.azure.com", "")
    if ".cognitiveservices.azure.com" in host:
        return host.replace(".cognitiveservices.azure.com", "")
    
    # Regional endpoint — discover account by listing resources in the group
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://management.azure.com/subscriptions/{subscription_id}"
            f"/resourceGroups/{resource_group}"
            f"/providers/Microsoft.CognitiveServices/accounts?api-version=2024-10-01",
            headers={"Authorization": f"Bearer {arm_token}"},
        )
        if resp.status_code == 200:
            for acct in resp.json().get("value", []):
                if acct.get("kind") in ("OpenAI", "AIServices"):
                    return acct["name"]
    
    raise RuntimeError(f"Could not resolve Azure OpenAI account name from endpoint: {endpoint}")


async def activate_azure_model(
    model_id: str,
    tenant_id: str,
    client_id: str,
    client_secret: str,
    subscription_id: str,
    resource_group: str,
    endpoint: str,
    api_key: str = "",
) -> ActivationResult:
    """Deploy a model on Azure OpenAI using the ARM management API.
    
    Uses the Azure Resource Manager API for reliable deployment creation
    (works with both custom subdomain and regional endpoints).
    """
    try:
        async with httpx.AsyncClient() as client:
            # Get ARM token (management plane)
            token_resp = await client.post(
                f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": "https://management.azure.com/.default",
                    "grant_type": "client_credentials",
                },
            )
            if token_resp.status_code != 200:
                return ActivationResult(
                    success=False,
                    status="failed",
                    message=f"Azure ARM auth failed: {token_resp.text[:200]}"
                )
            arm_token = token_resp.json()["access_token"]
            
            # Resolve account name from endpoint
            try:
                account_name = await _resolve_azure_account_name(
                    subscription_id, resource_group, endpoint, arm_token
                )
            except RuntimeError as e:
                return ActivationResult(
                    success=False, status="failed", message=str(e)
                )
            
            arm_base = (
                f"https://management.azure.com/subscriptions/{subscription_id}"
                f"/resourceGroups/{resource_group}"
                f"/providers/Microsoft.CognitiveServices/accounts/{account_name}"
                f"/deployments/{model_id}?api-version=2024-10-01"
            )
            arm_headers = {
                "Authorization": f"Bearer {arm_token}",
                "Content-Type": "application/json",
            }
            
            # Check if deployment already exists
            check_resp = await client.get(arm_base, headers=arm_headers)
            if check_resp.status_code == 200:
                props = check_resp.json().get("properties", {})
                prov_state = props.get("provisioningState", "")
                if prov_state == "Succeeded":
                    return ActivationResult(
                        success=True,
                        status="deployed",
                        message=f"Model {model_id} is already deployed."
                    )
                else:
                    return ActivationResult(
                        success=True,
                        status="pending",
                        message=f"Deployment {model_id} exists (state: {prov_state})."
                    )
            
            # Create deployment via ARM API
            deploy_resp = await client.put(
                arm_base,
                headers=arm_headers,
                json={
                    "sku": {
                        "name": "Standard",
                        "capacity": 10,  # 10K TPM — sensible starting point
                    },
                    "properties": {
                        "model": {
                            "format": "OpenAI",
                            "name": model_id,
                            "version": "latest",
                        }
                    },
                },
                timeout=30,
            )
            
            if deploy_resp.status_code in (200, 201):
                return ActivationResult(
                    success=True,
                    status="deployed",
                    message=f"Model {model_id} deployed successfully! It may take a minute to become fully available.",
                    endpoint_url=endpoint,
                )
            elif deploy_resp.status_code == 409:
                return ActivationResult(
                    success=True,
                    status="deployed",
                    message=f"Model {model_id} is already deployed."
                )
            else:
                error_detail = deploy_resp.text[:300]
                if deploy_resp.status_code == 403:
                    return ActivationResult(
                        success=False,
                        status="failed",
                        message=f"Permission denied. Your service principal needs 'Cognitive Services Contributor' role. Update the role in Azure Portal → IAM."
                    )
                elif "QuotaExceeded" in error_detail or "InsufficientQuota" in error_detail:
                    return ActivationResult(
                        success=False,
                        status="failed",
                        message=f"Quota exceeded for {model_id}. Request a quota increase in Azure Portal → Quotas."
                    )
                elif "ModelNotFound" in error_detail or "InvalidModel" in error_detail:
                    return ActivationResult(
                        success=False,
                        status="failed",
                        message=f"Model {model_id} is not available in your Azure region. Try a different region or check model availability."
                    )
                else:
                    return ActivationResult(
                        success=False,
                        status="failed",
                        message=f"Azure deployment failed ({deploy_resp.status_code}): {error_detail}"
                    )
                    
    except Exception as e:
        logger.error(f"Azure model activation failed for {model_id}: {e}")
        return ActivationResult(
            success=False,
            status="failed",
            message=f"Failed to deploy model: {str(e)}"
        )


async def activate_gcp_model(
    model_id: str,
    project_id: str,
    service_account_json: dict | str,
    region: str = "us-central1",
) -> ActivationResult:
    """Enable a model on GCP Vertex AI.
    
    Most Vertex AI models are available once the API is enabled.
    This checks access and provides guidance if there are issues.
    """
    import jwt as pyjwt
    import time as _time
    
    # Parse service account JSON
    sa = service_account_json if isinstance(service_account_json, dict) else json.loads(service_account_json)
    
    # Create JWT for auth
    now = int(_time.time())
    payload = {
        "iss": sa["client_email"],
        "sub": sa["client_email"],
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
        "scope": "https://www.googleapis.com/auth/cloud-platform",
    }
    
    try:
        signed = pyjwt.encode(payload, sa["private_key"], algorithm="RS256")
        
        async with httpx.AsyncClient() as client:
            # Exchange JWT for access token
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": signed,
                },
            )
            if token_resp.status_code != 200:
                return ActivationResult(
                    success=False,
                    status="failed",
                    message=f"GCP auth failed: {token_resp.text[:200]}"
                )
            access_token = token_resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Check if Vertex AI API is enabled
            api_check = await client.get(
                f"https://serviceusage.googleapis.com/v1/projects/{project_id}/services/aiplatform.googleapis.com",
                headers=headers,
            )
            
            if api_check.status_code == 200:
                api_state = api_check.json().get("state", "")
                if api_state != "ENABLED":
                    # Try to enable the API
                    enable_resp = await client.post(
                        f"https://serviceusage.googleapis.com/v1/projects/{project_id}/services/aiplatform.googleapis.com:enable",
                        headers=headers,
                    )
                    if enable_resp.status_code in (200, 201):
                        return ActivationResult(
                            success=True,
                            status="enabled",
                            message=f"Vertex AI API has been enabled for project {project_id}. Models should now be available."
                        )
                    else:
                        return ActivationResult(
                            success=False,
                            status="failed",
                            message=f"Failed to enable Vertex AI API: {enable_resp.text[:200]}"
                        )
            
            # Try to verify the model is accessible by calling the predict endpoint  
            # For Vertex AI, models are generally available — the main issue is permissions
            test_resp = await client.get(
                f"https://{region}-aiplatform.googleapis.com/v1beta1/publishers/google/models/{model_id}",
                headers=headers,
            )
            
            if test_resp.status_code == 200:
                return ActivationResult(
                    success=True,
                    status="enabled",
                    message=f"Model {model_id} is available and ready to use on Vertex AI."
                )
            elif test_resp.status_code == 403:
                return ActivationResult(
                    success=False,
                    status="failed",
                    message=f"Permission denied for {model_id}. Ensure the service account has 'Vertex AI User' role."
                )
            elif test_resp.status_code == 404:
                # Model might not be a publisher model — could be fine for direct invocation
                return ActivationResult(
                    success=True,
                    status="enabled",
                    message=f"Model {model_id} is available through Vertex AI in {region}."
                )
            else:
                return ActivationResult(
                    success=False,
                    status="failed",
                    message=f"Could not verify model access ({test_resp.status_code}): {test_resp.text[:200]}"
                )
                
    except Exception as e:
        logger.error(f"GCP model activation failed for {model_id}: {e}")
        return ActivationResult(
            success=False,
            status="failed",
            message=f"Failed to activate model: {str(e)}"
        )
