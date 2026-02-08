"""Map compliance checks to regulatory frameworks."""

from __future__ import annotations

# check_id prefix → list of frameworks it applies to
FRAMEWORK_MAPPING: dict[str, list[str]] = {
    # AWS checks
    "aws.bedrock.logging_enabled":       ["SOC2", "HIPAA", "GDPR", "ISO27001"],
    "aws.iam.overly_permissive_policies": ["SOC2", "HIPAA", "ISO27001"],
    "aws.encryption.ebs_default":        ["SOC2", "HIPAA", "GDPR", "ISO27001"],
    "aws.logging.cloudtrail_active":     ["SOC2", "HIPAA", "GDPR", "ISO27001"],
    # Azure checks
    "azure.ai_services.network_rules":   ["SOC2", "HIPAA", "ISO27001"],
    "azure.rbac.broad_roles":            ["SOC2", "HIPAA", "ISO27001"],
    "azure.logging.diagnostic_settings": ["SOC2", "HIPAA", "GDPR", "ISO27001"],
    # GCP checks
    "gcp.vertex.sa_permissions":         ["SOC2", "HIPAA", "ISO27001"],
    "gcp.logging.audit_config":          ["SOC2", "HIPAA", "GDPR", "ISO27001"],
    "gcp.network.vpc_service_controls":  ["SOC2", "HIPAA", "ISO27001"],
}

FRAMEWORK_INFO = {
    "SOC2": {
        "display_name": "SOC 2 Type II",
        "description": "Service Organization Control 2 — security, availability, processing integrity, confidentiality, and privacy",
    },
    "HIPAA": {
        "display_name": "HIPAA",
        "description": "Health Insurance Portability and Accountability Act — safeguards for protected health information",
    },
    "GDPR": {
        "display_name": "GDPR",
        "description": "General Data Protection Regulation — EU data protection and privacy regulation",
    },
    "ISO27001": {
        "display_name": "ISO 27001",
        "description": "International standard for information security management systems (ISMS)",
    },
}


def get_frameworks_for_check(check_id: str) -> list[str]:
    """Return framework names that a check maps to."""
    return FRAMEWORK_MAPPING.get(check_id, [])
