from app.services.iac_templates.aws import generate_aws_iac
from app.services.iac_templates.azure import generate_azure_iac
from app.services.iac_templates.gcp import generate_gcp_iac

GENERATORS = {
    "aws": generate_aws_iac,
    "azure": generate_azure_iac,
    "gcp": generate_gcp_iac,
}


def generate_iac(provider: str, iac_tool: str, **kwargs) -> dict:
    """Generate IaC code for a provider+tool combination.

    Returns dict with:
      - files: list of {filename, content} for multi-file templates
      - code: combined view for display (backward compat)
      - filename: primary filename
      - instructions: list of steps
      - security_notes: list of notes
    """
    generator = GENERATORS.get(provider)
    if not generator:
        raise ValueError(f"Unsupported provider: {provider}")

    # Only enable KB storage permissions for the chosen storage provider.
    # If kb_storage_provider doesn't match this provider, suppress the flag
    # so this template doesn't include storage blocks.
    kb_storage_provider = kwargs.pop("kb_storage_provider", None)
    if kwargs.get("enable_knowledge_base") and kb_storage_provider != provider:
        kwargs["enable_knowledge_base"] = False

    return generator(iac_tool, **kwargs)
