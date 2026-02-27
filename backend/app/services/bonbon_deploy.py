"""
BonBon Deploy Service

Handles auto model selection and Solution Kit deployment orchestration.
"""

import uuid
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud_provider import CloudProvider
from app.models.agent import Agent
from app.models.project import Project
from app.models.organization import Organization
from app.services.bonbon_templates import (
    get_template,
    render_system_prompt,
    SolutionKitTemplate,
)


# ─── Model Selection ───

# Cost tiers: lower number = cheaper/faster, higher = stronger
MODEL_CATALOG = {
    "gcp": {
        "primary": {"model_id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "provider": "gcp", "tier": "fast", "cost_rank": 1},
        "fallback": {"model_id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "gcp", "tier": "strong", "cost_rank": 3},
    },
    "aws": {
        "primary": {"model_id": "amazon.nova-lite-v1:0", "name": "Nova Lite", "provider": "aws", "tier": "fast", "cost_rank": 2},
        "fallback": {"model_id": "amazon.nova-pro-v1:0", "name": "Nova Pro", "provider": "aws", "tier": "strong", "cost_rank": 4},
    },
    "azure": {
        "primary": {"model_id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "azure", "tier": "fast", "cost_rank": 2},
        "fallback": {"model_id": "gpt-4o", "name": "GPT-4o", "provider": "azure", "tier": "strong", "cost_rank": 5},
    },
}


@dataclass
class ModelRecommendation:
    primary: Dict[str, Any]
    fallback: Dict[str, Any]
    providers: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary": self.primary,
            "fallback": self.fallback,
            "providers": self.providers,
        }


async def get_org_providers(db: AsyncSession, org_id: uuid.UUID) -> List[str]:
    """Get active cloud provider types for an organization."""
    stmt = select(CloudProvider.provider_type).where(
        and_(
            CloudProvider.org_id == org_id,
            CloudProvider.status == "active",
        )
    )
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]


async def recommend_models(db: AsyncSession, org_id: uuid.UUID) -> ModelRecommendation:
    """
    Recommend primary (cheapest/fastest) and fallback (strongest) models
    based on the org's connected cloud providers.
    """
    providers = await get_org_providers(db, org_id)

    if not providers:
        # Default to GCP if no providers connected
        return ModelRecommendation(
            primary=MODEL_CATALOG["gcp"]["primary"],
            fallback=MODEL_CATALOG["gcp"]["fallback"],
            providers=[],
        )

    # Collect all candidate models
    primaries = []
    fallbacks = []
    for provider in providers:
        if provider in MODEL_CATALOG:
            primaries.append(MODEL_CATALOG[provider]["primary"])
            fallbacks.append(MODEL_CATALOG[provider]["fallback"])

    if not primaries:
        # Provider types not recognized, default to GCP
        return ModelRecommendation(
            primary=MODEL_CATALOG["gcp"]["primary"],
            fallback=MODEL_CATALOG["gcp"]["fallback"],
            providers=providers,
        )

    # Pick cheapest primary, strongest fallback
    primary = min(primaries, key=lambda m: m["cost_rank"])
    fallback = max(fallbacks, key=lambda m: m["cost_rank"])

    return ModelRecommendation(
        primary=primary,
        fallback=fallback,
        providers=providers,
    )


# ─── Deploy Orchestration ───

@dataclass
class DeployRequest:
    template_id: str
    project_id: uuid.UUID
    name: Optional[str] = None
    company_name: str = "our company"
    tone: Optional[str] = None
    industry: Optional[str] = None
    model_id: Optional[str] = None  # Override auto-selection
    widget_enabled: Optional[bool] = None
    welcome_message: Optional[str] = None
    suggested_questions: Optional[List[str]] = None


@dataclass
class DeployResult:
    agent: Agent
    model_recommendation: ModelRecommendation
    template_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": str(self.agent.id),
            "agent_name": self.agent.name,
            "template_id": self.template_id,
            "model_used": self.agent.model_id,
            "widget_enabled": self.agent.widget_enabled if hasattr(self.agent, "widget_enabled") else False,
        }


async def deploy_solution_kit(
    db: AsyncSession,
    org_id: uuid.UUID,
    request: DeployRequest,
) -> DeployResult:
    """
    Deploy a Solution Kit by creating an agent from a template with customizations.

    1. Load template
    2. Auto-select model (or use override)
    3. Render system prompt with company name and tone
    4. Create Agent in DB
    5. Return result
    """
    # 1. Load template
    template = get_template(request.template_id)
    if not template:
        raise ValueError(f"Unknown template: {request.template_id}")

    # 2. Verify project exists and belongs to org
    stmt = select(Project).where(
        and_(
            Project.id == request.project_id,
            Project.org_id == org_id,
        )
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise ValueError("Project not found or does not belong to this organization")

    # 3. Auto-select model
    model_rec = await recommend_models(db, org_id)
    model_id = request.model_id or model_rec.primary["model_id"]

    # 4. Render system prompt
    system_prompt = render_system_prompt(
        template,
        company_name=request.company_name,
        tone=request.tone,
    )

    # 5. Build agent name
    agent_name = request.name or f"{template.name}"

    # 6. Build bonbon config
    bonbon_config = {
        "tone": request.tone or template.suggested_tone,
        "company_name": request.company_name,
        "industry": request.industry,
    }

    # 7. Build widget config
    widget_enabled = request.widget_enabled if request.widget_enabled is not None else template.widget_enabled
    widget_config = dict(template.default_widget_config)
    if request.welcome_message:
        widget_config["welcome_message"] = request.welcome_message
    if request.suggested_questions:
        widget_config["suggested_questions"] = request.suggested_questions

    # 8. Create the agent
    agent = Agent(
        project_id=request.project_id,
        org_id=org_id,
        name=agent_name,
        description=template.description,
        system_prompt=system_prompt,
        model_id=model_id,
        model_config=template.model_config,
        knowledge_base_ids=[],
        tool_policy=template.tool_policy,
        bonbon_template_id=request.template_id,
        bonbon_config=bonbon_config,
        widget_enabled=widget_enabled,
        widget_config=widget_config,
    )

    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return DeployResult(
        agent=agent,
        model_recommendation=model_rec,
        template_id=request.template_id,
    )
