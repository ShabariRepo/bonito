"""
BonBon API Routes

Solution Kit templates, model recommendations, and deployment endpoints.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.bonobot import AgentResponse
from app.services.bonbon_templates import get_all_templates, get_template
from app.services.bonbon_deploy import (
    recommend_models,
    deploy_solution_kit,
    DeployRequest,
)

router = APIRouter(prefix="/bonbon", tags=["bonbon"])


# ─── Schemas ───

class DeployRequestSchema(BaseModel):
    template_id: str
    project_id: UUID
    name: Optional[str] = Field(None, max_length=255)
    company_name: str = Field("our company", max_length=255)
    tone: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    model_id: Optional[str] = Field(None, max_length=100)
    widget_enabled: Optional[bool] = None
    welcome_message: Optional[str] = Field(None, max_length=500)
    suggested_questions: Optional[List[str]] = None


class DeployResponseSchema(BaseModel):
    agent: AgentResponse
    template_id: str
    model_recommendation: Dict[str, Any]


# ─── Routes ───

@router.get("/templates")
async def list_templates(
    current_user: User = Depends(get_current_user),
):
    """List all available Solution Kit templates."""
    return get_all_templates()


@router.get("/templates/{template_id}")
async def get_template_detail(
    template_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get details for a specific Solution Kit template."""
    template = get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )
    return template.to_dict()


@router.get("/recommend-models")
async def get_model_recommendations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recommended models based on the org's connected cloud providers."""
    rec = await recommend_models(db, current_user.org_id)
    return rec.to_dict()


@router.post("/deploy", response_model=DeployResponseSchema, status_code=status.HTTP_201_CREATED)
async def deploy_kit(
    body: DeployRequestSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deploy a Solution Kit — creates an agent from a template with customizations."""
    # Validate template exists
    template = get_template(body.template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{body.template_id}' not found",
        )

    try:
        result = await deploy_solution_kit(
            db=db,
            org_id=current_user.org_id,
            request=DeployRequest(
                template_id=body.template_id,
                project_id=body.project_id,
                name=body.name,
                company_name=body.company_name,
                tone=body.tone,
                industry=body.industry,
                model_id=body.model_id,
                widget_enabled=body.widget_enabled,
                welcome_message=body.welcome_message,
                suggested_questions=body.suggested_questions,
            ),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return DeployResponseSchema(
        agent=AgentResponse.model_validate(result.agent),
        template_id=result.template_id,
        model_recommendation=result.model_recommendation.to_dict(),
    )
