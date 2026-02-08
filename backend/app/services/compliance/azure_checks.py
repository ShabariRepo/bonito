"""Real Azure compliance checks using Azure REST APIs."""

import logging
from typing import Optional

import httpx

from app.services.compliance.base import (
    BaseChecker,
    CheckResult,
    CheckSeverity,
    ComplianceCheck,
)

logger = logging.getLogger(__name__)

# Overly broad built-in role IDs
OVERLY_BROAD_ROLES = {
    "8e3af657-a8ff-443c-a75c-2fe8c4bcb635": "Owner",
    "b24988ac-6180-42a0-ab88-20f7382dd24c": "Contributor",
    "18d7d88d-d35e-4fb5-a5c3-7773c20a72d9": "User Access Administrator",
}


class AzureComplianceChecker(BaseChecker):
    provider = "azure"

    def __init__(self, tenant_id: str, client_id: str, client_secret: str, subscription_id: str):
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._subscription_id = subscription_id
        self._token: Optional[str] = None

    async def _get_token(self) -> str:
        if self._token:
            return self._token
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "scope": "https://management.azure.com/.default",
                },
            )
            resp.raise_for_status()
            self._token = resp.json()["access_token"]
            return self._token

    def _headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def run_all(self) -> list[ComplianceCheck]:
        checks: list[ComplianceCheck] = []
        for fn in [
            self._check_ai_services_network_rules,
            self._check_rbac_broad_roles,
            self._check_diagnostic_settings,
        ]:
            try:
                result = await fn()
                if isinstance(result, list):
                    checks.extend(result)
                else:
                    checks.append(result)
            except Exception as e:
                logger.error(f"Azure compliance check {fn.__name__} failed: {e}")
                checks.append(ComplianceCheck(
                    check_id=f"azure.{fn.__name__.removeprefix('_check_')}",
                    check_name=fn.__name__.removeprefix("_check_").replace("_", " ").title(),
                    category="error",
                    provider="azure",
                    result=CheckResult.ERROR,
                    severity=CheckSeverity.HIGH,
                    details={"error": str(e)},
                ))
        return checks

    async def _check_ai_services_network_rules(self) -> ComplianceCheck:
        """Check if Azure Cognitive/AI services restrict public network access."""
        token = await self._get_token()
        url = (
            f"https://management.azure.com/subscriptions/{self._subscription_id}"
            f"/providers/Microsoft.CognitiveServices/accounts"
            f"?api-version=2023-05-01"
        )
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers(token))
            if resp.status_code == 403:
                return ComplianceCheck(
                    check_id="azure.ai_services.network_rules",
                    check_name="AI Services Network Access Restrictions",
                    category="network",
                    provider="azure",
                    result=CheckResult.WARNING,
                    severity=CheckSeverity.HIGH,
                    details={"finding": "Insufficient permissions to check AI services"},
                    remediation="Grant Reader role on Cognitive Services resources",
                )
            resp.raise_for_status()
            accounts = resp.json().get("value", [])

        if not accounts:
            return ComplianceCheck(
                check_id="azure.ai_services.network_rules",
                check_name="AI Services Network Access Restrictions",
                category="network",
                provider="azure",
                result=CheckResult.PASS,
                severity=CheckSeverity.HIGH,
                details={"finding": "No AI/Cognitive Services accounts found"},
            )

        publicly_accessible = []
        for acct in accounts:
            props = acct.get("properties", {})
            network_rules = props.get("networkAcls", {})
            public_access = props.get("publicNetworkAccess", "Enabled")
            default_action = network_rules.get("defaultAction", "Allow")
            if public_access == "Enabled" and default_action == "Allow":
                publicly_accessible.append(acct.get("name", "unknown"))

        if publicly_accessible:
            return ComplianceCheck(
                check_id="azure.ai_services.network_rules",
                check_name="AI Services Network Access Restrictions",
                category="network",
                provider="azure",
                result=CheckResult.FAIL,
                severity=CheckSeverity.HIGH,
                details={
                    "finding": f"{len(publicly_accessible)} AI service(s) allow unrestricted public access",
                    "resources": publicly_accessible[:20],
                },
                remediation="Restrict network access using private endpoints or IP firewall rules",
            )
        return ComplianceCheck(
            check_id="azure.ai_services.network_rules",
            check_name="AI Services Network Access Restrictions",
            category="network",
            provider="azure",
            result=CheckResult.PASS,
            severity=CheckSeverity.HIGH,
            details={"finding": "All AI services have network access restrictions configured"},
        )

    async def _check_rbac_broad_roles(self) -> ComplianceCheck:
        """Check for overly broad RBAC role assignments (Owner/Contributor at subscription scope)."""
        token = await self._get_token()
        url = (
            f"https://management.azure.com/subscriptions/{self._subscription_id}"
            f"/providers/Microsoft.Authorization/roleAssignments"
            f"?api-version=2022-04-01"
        )
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers(token))
            if resp.status_code == 403:
                return ComplianceCheck(
                    check_id="azure.rbac.broad_roles",
                    check_name="RBAC Overly Broad Role Assignments",
                    category="access",
                    provider="azure",
                    result=CheckResult.WARNING,
                    severity=CheckSeverity.CRITICAL,
                    details={"finding": "Insufficient permissions to check RBAC assignments"},
                    remediation="Grant Reader role on the subscription",
                )
            resp.raise_for_status()
            assignments = resp.json().get("value", [])

        broad_assignments = []
        for assignment in assignments:
            props = assignment.get("properties", {})
            role_def_id = props.get("roleDefinitionId", "")
            # Extract the role GUID from the full resource ID
            role_guid = role_def_id.rsplit("/", 1)[-1] if "/" in role_def_id else role_def_id
            scope = props.get("scope", "")
            # Only flag subscription-level broad roles
            if role_guid in OVERLY_BROAD_ROLES and scope == f"/subscriptions/{self._subscription_id}":
                broad_assignments.append({
                    "role": OVERLY_BROAD_ROLES[role_guid],
                    "principal_id": props.get("principalId", ""),
                    "scope": scope,
                })

        if len(broad_assignments) > 5:
            return ComplianceCheck(
                check_id="azure.rbac.broad_roles",
                check_name="RBAC Overly Broad Role Assignments",
                category="access",
                provider="azure",
                result=CheckResult.WARNING,
                severity=CheckSeverity.CRITICAL,
                details={
                    "finding": f"{len(broad_assignments)} broad role assignments at subscription scope",
                    "assignments": broad_assignments[:10],
                },
                remediation="Apply least-privilege principle; use custom roles scoped to resource groups",
            )
        return ComplianceCheck(
            check_id="azure.rbac.broad_roles",
            check_name="RBAC Overly Broad Role Assignments",
            category="access",
            provider="azure",
            result=CheckResult.PASS,
            severity=CheckSeverity.CRITICAL,
            details={
                "finding": f"{len(broad_assignments)} broad role assignments at subscription scope (within acceptable range)",
            },
        )

    async def _check_diagnostic_settings(self) -> ComplianceCheck:
        """Check if diagnostic settings are enabled on the subscription."""
        token = await self._get_token()
        url = (
            f"https://management.azure.com/subscriptions/{self._subscription_id}"
            f"/providers/Microsoft.Insights/diagnosticSettings"
            f"?api-version=2021-05-01-preview"
        )
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers(token))
            if resp.status_code == 403:
                return ComplianceCheck(
                    check_id="azure.logging.diagnostic_settings",
                    check_name="Diagnostic Settings Enabled",
                    category="logging",
                    provider="azure",
                    result=CheckResult.WARNING,
                    severity=CheckSeverity.HIGH,
                    details={"finding": "Insufficient permissions to check diagnostic settings"},
                    remediation="Grant Monitoring Reader role",
                )
            resp.raise_for_status()
            settings = resp.json().get("value", [])

        if settings:
            names = [s.get("name", "unknown") for s in settings]
            return ComplianceCheck(
                check_id="azure.logging.diagnostic_settings",
                check_name="Diagnostic Settings Enabled",
                category="logging",
                provider="azure",
                result=CheckResult.PASS,
                severity=CheckSeverity.HIGH,
                details={
                    "finding": f"{len(settings)} diagnostic setting(s) configured",
                    "settings": names[:10],
                },
            )
        return ComplianceCheck(
            check_id="azure.logging.diagnostic_settings",
            check_name="Diagnostic Settings Enabled",
            category="logging",
            provider="azure",
            result=CheckResult.FAIL,
            severity=CheckSeverity.HIGH,
            details={"finding": "No diagnostic settings configured at subscription level"},
            remediation="Enable diagnostic settings to route activity logs to Log Analytics, Storage, or Event Hub",
        )
