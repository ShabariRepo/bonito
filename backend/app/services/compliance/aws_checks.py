"""Real AWS compliance checks using boto3/aioboto3."""

import logging
from typing import Optional

import aioboto3
from botocore.exceptions import ClientError

from app.services.compliance.base import (
    BaseChecker,
    CheckResult,
    CheckSeverity,
    ComplianceCheck,
)

logger = logging.getLogger(__name__)


class AWSComplianceChecker(BaseChecker):
    provider = "aws"

    def __init__(self, access_key_id: str, secret_access_key: str, region: str = "us-east-1"):
        self._session = aioboto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )
        self._region = region

    async def run_all(self) -> list[ComplianceCheck]:
        checks: list[ComplianceCheck] = []
        for fn in [
            self._check_bedrock_logging,
            self._check_iam_overly_permissive,
            self._check_encryption_at_rest,
            self._check_cloudtrail_status,
        ]:
            try:
                result = await fn()
                if isinstance(result, list):
                    checks.extend(result)
                else:
                    checks.append(result)
            except Exception as e:
                logger.error(f"AWS compliance check {fn.__name__} failed: {e}")
                checks.append(ComplianceCheck(
                    check_id=f"aws.{fn.__name__.removeprefix('_check_')}",
                    check_name=fn.__name__.removeprefix("_check_").replace("_", " ").title(),
                    category="error",
                    provider="aws",
                    result=CheckResult.ERROR,
                    severity=CheckSeverity.HIGH,
                    details={"error": str(e)},
                ))
        return checks

    async def _check_bedrock_logging(self) -> ComplianceCheck:
        """Check if Bedrock model invocation logging is enabled."""
        try:
            async with self._session.client("bedrock") as bedrock:
                resp = await bedrock.get_model_invocation_logging_configuration()
                config = resp.get("loggingConfig", {})
                s3_enabled = config.get("s3Config", {}).get("bucketName") is not None
                cw_enabled = config.get("cloudWatchConfig", {}).get("logGroupName") is not None

                if s3_enabled or cw_enabled:
                    destinations = []
                    if s3_enabled:
                        destinations.append(f"S3: {config['s3Config']['bucketName']}")
                    if cw_enabled:
                        destinations.append(f"CloudWatch: {config['cloudWatchConfig']['logGroupName']}")
                    return ComplianceCheck(
                        check_id="aws.bedrock.logging_enabled",
                        check_name="Bedrock Model Invocation Logging",
                        category="logging",
                        provider="aws",
                        result=CheckResult.PASS,
                        severity=CheckSeverity.CRITICAL,
                        details={"destinations": destinations, "finding": "Model invocation logging is enabled"},
                    )
                else:
                    return ComplianceCheck(
                        check_id="aws.bedrock.logging_enabled",
                        check_name="Bedrock Model Invocation Logging",
                        category="logging",
                        provider="aws",
                        result=CheckResult.FAIL,
                        severity=CheckSeverity.CRITICAL,
                        details={"finding": "Model invocation logging is not enabled"},
                        remediation="Enable Bedrock model invocation logging to S3 or CloudWatch in the AWS Console or via API",
                    )
        except ClientError as e:
            if e.response["Error"]["Code"] == "AccessDeniedException":
                return ComplianceCheck(
                    check_id="aws.bedrock.logging_enabled",
                    check_name="Bedrock Model Invocation Logging",
                    category="logging",
                    provider="aws",
                    result=CheckResult.WARNING,
                    severity=CheckSeverity.CRITICAL,
                    details={"finding": "Insufficient permissions to check Bedrock logging"},
                    remediation="Grant bedrock:GetModelInvocationLoggingConfiguration permission",
                )
            raise

    async def _check_iam_overly_permissive(self) -> list[ComplianceCheck]:
        """Check IAM policies for overly permissive access (Action: * or Resource: *)."""
        checks = []
        try:
            async with self._session.client("iam") as iam:
                paginator = iam.get_paginator("list_policies")
                overly_permissive = []
                async for page in paginator.paginate(Scope="Local", MaxItems=100):
                    for policy in page.get("Policies", []):
                        arn = policy["Arn"]
                        vid = policy.get("DefaultVersionId", "v1")
                        try:
                            ver_resp = await iam.get_policy_version(PolicyArn=arn, VersionId=vid)
                            doc = ver_resp["PolicyVersion"]["Document"]
                            if isinstance(doc, str):
                                import json
                                doc = json.loads(doc)
                            statements = doc.get("Statement", [])
                            if isinstance(statements, dict):
                                statements = [statements]
                            for stmt in statements:
                                if stmt.get("Effect") != "Allow":
                                    continue
                                actions = stmt.get("Action", [])
                                resources = stmt.get("Resource", [])
                                if isinstance(actions, str):
                                    actions = [actions]
                                if isinstance(resources, str):
                                    resources = [resources]
                                if "*" in actions and "*" in resources:
                                    overly_permissive.append(policy["PolicyName"])
                                    break
                        except ClientError:
                            continue

                if overly_permissive:
                    checks.append(ComplianceCheck(
                        check_id="aws.iam.overly_permissive_policies",
                        check_name="IAM Overly Permissive Policies",
                        category="access",
                        provider="aws",
                        result=CheckResult.FAIL,
                        severity=CheckSeverity.CRITICAL,
                        details={
                            "finding": f"{len(overly_permissive)} policies with Action:* and Resource:*",
                            "policies": overly_permissive[:20],
                        },
                        remediation="Replace wildcard policies with least-privilege permissions",
                    ))
                else:
                    checks.append(ComplianceCheck(
                        check_id="aws.iam.overly_permissive_policies",
                        check_name="IAM Overly Permissive Policies",
                        category="access",
                        provider="aws",
                        result=CheckResult.PASS,
                        severity=CheckSeverity.CRITICAL,
                        details={"finding": "No customer-managed policies with full wildcard access found"},
                    ))
        except ClientError as e:
            if e.response["Error"]["Code"] == "AccessDenied":
                checks.append(ComplianceCheck(
                    check_id="aws.iam.overly_permissive_policies",
                    check_name="IAM Overly Permissive Policies",
                    category="access",
                    provider="aws",
                    result=CheckResult.WARNING,
                    severity=CheckSeverity.CRITICAL,
                    details={"finding": "Insufficient permissions to audit IAM policies"},
                    remediation="Grant iam:ListPolicies and iam:GetPolicyVersion permissions",
                ))
            else:
                raise
        return checks

    async def _check_encryption_at_rest(self) -> ComplianceCheck:
        """Check if default EBS encryption is enabled in the region."""
        try:
            async with self._session.client("ec2") as ec2:
                resp = await ec2.get_ebs_encryption_by_default()
                enabled = resp.get("EbsEncryptionByDefault", False)
                if enabled:
                    return ComplianceCheck(
                        check_id="aws.encryption.ebs_default",
                        check_name="EBS Encryption at Rest (Default)",
                        category="encryption",
                        provider="aws",
                        result=CheckResult.PASS,
                        severity=CheckSeverity.CRITICAL,
                        details={"finding": f"Default EBS encryption enabled in {self._region}"},
                    )
                else:
                    return ComplianceCheck(
                        check_id="aws.encryption.ebs_default",
                        check_name="EBS Encryption at Rest (Default)",
                        category="encryption",
                        provider="aws",
                        result=CheckResult.FAIL,
                        severity=CheckSeverity.CRITICAL,
                        details={"finding": f"Default EBS encryption NOT enabled in {self._region}"},
                        remediation="Enable default EBS encryption via EC2 console or ec2:EnableEbsEncryptionByDefault",
                    )
        except ClientError as e:
            if e.response["Error"]["Code"] == "UnauthorizedOperation":
                return ComplianceCheck(
                    check_id="aws.encryption.ebs_default",
                    check_name="EBS Encryption at Rest (Default)",
                    category="encryption",
                    provider="aws",
                    result=CheckResult.WARNING,
                    severity=CheckSeverity.CRITICAL,
                    details={"finding": "Insufficient permissions to check EBS encryption"},
                    remediation="Grant ec2:GetEbsEncryptionByDefault permission",
                )
            raise

    async def _check_cloudtrail_status(self) -> ComplianceCheck:
        """Check if CloudTrail is enabled with at least one active trail."""
        try:
            async with self._session.client("cloudtrail") as ct:
                resp = await ct.describe_trails()
                trails = resp.get("trailList", [])
                active_trails = []
                for trail in trails:
                    name = trail.get("Name", "")
                    try:
                        status_resp = await ct.get_trail_status(Name=trail["TrailARN"])
                        if status_resp.get("IsLogging", False):
                            active_trails.append(name)
                    except ClientError:
                        continue

                if active_trails:
                    return ComplianceCheck(
                        check_id="aws.logging.cloudtrail_active",
                        check_name="CloudTrail Active",
                        category="logging",
                        provider="aws",
                        result=CheckResult.PASS,
                        severity=CheckSeverity.CRITICAL,
                        details={
                            "finding": f"{len(active_trails)} active CloudTrail trail(s)",
                            "trails": active_trails,
                        },
                    )
                else:
                    return ComplianceCheck(
                        check_id="aws.logging.cloudtrail_active",
                        check_name="CloudTrail Active",
                        category="logging",
                        provider="aws",
                        result=CheckResult.FAIL,
                        severity=CheckSeverity.CRITICAL,
                        details={"finding": "No active CloudTrail trails found"},
                        remediation="Enable CloudTrail logging for audit and compliance tracking",
                    )
        except ClientError as e:
            if e.response["Error"]["Code"] == "AccessDeniedException":
                return ComplianceCheck(
                    check_id="aws.logging.cloudtrail_active",
                    check_name="CloudTrail Active",
                    category="logging",
                    provider="aws",
                    result=CheckResult.WARNING,
                    severity=CheckSeverity.CRITICAL,
                    details={"finding": "Insufficient permissions to check CloudTrail"},
                    remediation="Grant cloudtrail:DescribeTrails and cloudtrail:GetTrailStatus permissions",
                )
            raise
