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
    return generator(iac_tool, **kwargs)
