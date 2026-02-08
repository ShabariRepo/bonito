"""Real GCP compliance checks using REST APIs with service account auth."""

import json
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


class GCPComplianceChecker(BaseChecker):
    provider = "gcp"

    def __init__(self, project_id: str, service_account_json: str, region: str = "us-central1"):
        self._project_id = project_id
        self._region = region
        self._sa_info = json.loads(service_account_json) if isinstance(service_account_json, str) else service_account_json
        self._token: Optional[str] = None

    async def _get_token(self) -> str:
        """Get access token via service account JWT → token exchange."""
        if self._token:
            return self._token
        import time
        import jwt as pyjwt

        now = int(time.time())
        payload = {
            "iss": self._sa_info["client_email"],
            "scope": "https://www.googleapis.com/auth/cloud-platform",
            "aud": "https://oauth2.googleapis.com/token",
            "iat": now,
            "exp": now + 3600,
        }
        signed_jwt = pyjwt.encode(payload, self._sa_info["private_key"], algorithm="RS256")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": signed_jwt,
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
            self._check_vertex_sa_permissions,
            self._check_audit_logging,
            self._check_vpc_service_controls,
        ]:
            try:
                result = await fn()
                if isinstance(result, list):
                    checks.extend(result)
                else:
                    checks.append(result)
            except Exception as e:
                logger.error(f"GCP compliance check {fn.__name__} failed: {e}")
                checks.append(ComplianceCheck(
                    check_id=f"gcp.{fn.__name__.removeprefix('_check_')}",
                    check_name=fn.__name__.removeprefix("_check_").replace("_", " ").title(),
                    category="error",
                    provider="gcp",
                    result=CheckResult.ERROR,
                    severity=CheckSeverity.HIGH,
                    details={"error": str(e)},
                ))
        return checks

    async def _check_vertex_sa_permissions(self) -> ComplianceCheck:
        """Check if the Vertex AI service account has overly broad roles (Editor/Owner)."""
        token = await self._get_token()
        url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{self._project_id}:getIamPolicy"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self._headers(token), json={})
            if resp.status_code == 403:
                return ComplianceCheck(
                    check_id="gcp.vertex.sa_permissions",
                    check_name="Vertex AI Service Account Permissions",
                    category="access",
                    provider="gcp",
                    result=CheckResult.WARNING,
                    severity=CheckSeverity.CRITICAL,
                    details={"finding": "Insufficient permissions to check IAM policy"},
                    remediation="Grant resourcemanager.projects.getIamPolicy permission",
                )
            resp.raise_for_status()
            policy = resp.json()

        broad_roles = {"roles/editor", "roles/owner"}
        ai_sa_pattern = "aiplatform.googleapis.com"
        broad_bindings = []

        for binding in policy.get("bindings", []):
            role = binding.get("role", "")
            if role in broad_roles:
                for member in binding.get("members", []):
                    if ai_sa_pattern in member or "compute@developer" in member:
                        broad_bindings.append({"member": member, "role": role})

        if broad_bindings:
            return ComplianceCheck(
                check_id="gcp.vertex.sa_permissions",
                check_name="Vertex AI Service Account Permissions",
                category="access",
                provider="gcp",
                result=CheckResult.FAIL,
                severity=CheckSeverity.CRITICAL,
                details={
                    "finding": f"{len(broad_bindings)} AI-related service accounts with overly broad roles",
                    "bindings": broad_bindings[:10],
                },
                remediation="Replace Editor/Owner roles with specific Vertex AI roles (roles/aiplatform.user)",
            )
        return ComplianceCheck(
            check_id="gcp.vertex.sa_permissions",
            check_name="Vertex AI Service Account Permissions",
            category="access",
            provider="gcp",
            result=CheckResult.PASS,
            severity=CheckSeverity.CRITICAL,
            details={"finding": "No AI service accounts with overly broad roles found"},
        )

    async def _check_audit_logging(self) -> ComplianceCheck:
        """Check if audit logging is configured for the project."""
        token = await self._get_token()
        url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{self._project_id}:getIamPolicy"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers=self._headers(token),
                json={"options": {"requestedPolicyVersion": 3}},
            )
            if resp.status_code == 403:
                return ComplianceCheck(
                    check_id="gcp.logging.audit_config",
                    check_name="Audit Logging Configuration",
                    category="logging",
                    provider="gcp",
                    result=CheckResult.WARNING,
                    severity=CheckSeverity.CRITICAL,
                    details={"finding": "Insufficient permissions to check audit config"},
                    remediation="Grant resourcemanager.projects.getIamPolicy permission",
                )
            resp.raise_for_status()
            policy = resp.json()

        audit_configs = policy.get("auditConfigs", [])
        if audit_configs:
            services = [ac.get("service", "unknown") for ac in audit_configs]
            all_services = "allServices" in services
            return ComplianceCheck(
                check_id="gcp.logging.audit_config",
                check_name="Audit Logging Configuration",
                category="logging",
                provider="gcp",
                result=CheckResult.PASS if all_services else CheckResult.WARNING,
                severity=CheckSeverity.CRITICAL,
                details={
                    "finding": f"Audit logging configured for {len(services)} service(s)"
                    + (" including allServices" if all_services else " but allServices not included"),
                    "services": services[:20],
                },
                remediation=None if all_services else "Add audit logging for allServices to ensure full coverage",
            )
        return ComplianceCheck(
            check_id="gcp.logging.audit_config",
            check_name="Audit Logging Configuration",
            category="logging",
            provider="gcp",
            result=CheckResult.FAIL,
            severity=CheckSeverity.CRITICAL,
            details={"finding": "No audit logging configuration found"},
            remediation="Enable audit logging for allServices in the project IAM policy",
        )

    async def _check_vpc_service_controls(self) -> ComplianceCheck:
        """Check if VPC Service Controls are configured (access policies exist)."""
        token = await self._get_token()
        url = "https://accesscontextmanager.googleapis.com/v1/accessPolicies"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers(token))
            if resp.status_code == 403:
                return ComplianceCheck(
                    check_id="gcp.network.vpc_service_controls",
                    check_name="VPC Service Controls",
                    category="network",
                    provider="gcp",
                    result=CheckResult.WARNING,
                    severity=CheckSeverity.HIGH,
                    details={"finding": "Insufficient permissions to check VPC Service Controls"},
                    remediation="Grant accesscontextmanager.policies.list permission",
                )
            resp.raise_for_status()
            policies = resp.json().get("accessPolicies", [])

        if policies:
            # Check for service perimeters in the first policy
            policy_name = policies[0].get("name", "")
            perim_url = f"https://accesscontextmanager.googleapis.com/v1/{policy_name}/servicePerimeters"
            async with httpx.AsyncClient() as client:
                perim_resp = await client.get(perim_url, headers=self._headers(token))
                perimeters = perim_resp.json().get("servicePerimeters", []) if perim_resp.status_code == 200 else []

            if perimeters:
                return ComplianceCheck(
                    check_id="gcp.network.vpc_service_controls",
                    check_name="VPC Service Controls",
                    category="network",
                    provider="gcp",
                    result=CheckResult.PASS,
                    severity=CheckSeverity.HIGH,
                    details={
                        "finding": f"{len(perimeters)} service perimeter(s) configured",
                        "perimeters": [p.get("title", p.get("name", "")) for p in perimeters[:10]],
                    },
                )
            return ComplianceCheck(
                check_id="gcp.network.vpc_service_controls",
                check_name="VPC Service Controls",
                category="network",
                provider="gcp",
                result=CheckResult.WARNING,
                severity=CheckSeverity.HIGH,
                details={"finding": "Access policy exists but no service perimeters configured"},
                remediation="Create VPC Service Controls perimeters to restrict API access",
            )

        return ComplianceCheck(
            check_id="gcp.network.vpc_service_controls",
            check_name="VPC Service Controls",
            category="network",
            provider="gcp",
            result=CheckResult.FAIL,
            severity=CheckSeverity.HIGH,
            details={"finding": "No VPC Service Controls access policies found"},
            remediation="Set up VPC Service Controls to create security perimeters around GCP resources",
        )
