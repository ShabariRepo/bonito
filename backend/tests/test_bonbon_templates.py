"""
Tests for BonBon Solution Kit templates, model selection, deploy flow, and widget endpoints.
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.bonbon_templates import (
    get_all_templates,
    get_template,
    render_system_prompt,
    TEMPLATES,
)
from app.services.bonbon_deploy import (
    recommend_models,
    deploy_solution_kit,
    DeployRequest,
    ModelRecommendation,
    MODEL_CATALOG,
)


# ─── Template Tests ───


class TestTemplateRegistry:
    """Test that all 4 templates load correctly."""

    def test_all_templates_load(self):
        templates = get_all_templates()
        assert len(templates) == 4

    def test_template_ids(self):
        expected_ids = {"customer_service", "knowledge_assistant", "sales_qualifier", "content_assistant"}
        actual_ids = set(TEMPLATES.keys())
        assert actual_ids == expected_ids

    def test_get_template_by_id(self):
        for template_id in ["customer_service", "knowledge_assistant", "sales_qualifier", "content_assistant"]:
            template = get_template(template_id)
            assert template is not None
            assert template.id == template_id

    def test_get_template_not_found(self):
        template = get_template("nonexistent")
        assert template is None

    def test_template_has_required_fields(self):
        for template_id, template in TEMPLATES.items():
            assert template.id, f"{template_id}: missing id"
            assert template.name, f"{template_id}: missing name"
            assert template.description, f"{template_id}: missing description"
            assert template.icon, f"{template_id}: missing icon"
            assert template.category, f"{template_id}: missing category"
            assert template.system_prompt, f"{template_id}: missing system_prompt"
            assert template.model_config, f"{template_id}: missing model_config"
            assert template.tool_policy is not None, f"{template_id}: missing tool_policy"
            assert template.suggested_tone, f"{template_id}: missing suggested_tone"
            assert template.default_widget_config, f"{template_id}: missing default_widget_config"

    def test_system_prompts_are_substantial(self):
        """System prompts should be production-quality, not placeholders."""
        for template_id, template in TEMPLATES.items():
            word_count = len(template.system_prompt.split())
            assert word_count >= 150, f"{template_id}: system prompt too short ({word_count} words)"

    def test_system_prompts_have_placeholders(self):
        """System prompts should have {company_name} and {tone} placeholders."""
        for template_id, template in TEMPLATES.items():
            assert "{company_name}" in template.system_prompt, f"{template_id}: missing {{company_name}}"
            assert "{tone}" in template.system_prompt, f"{template_id}: missing {{tone}}"

    def test_template_to_dict(self):
        template = get_template("customer_service")
        d = template.to_dict()
        assert d["id"] == "customer_service"
        assert "system_prompt" in d
        assert "model_config" in d
        assert isinstance(d["tags"], list)

    def test_widget_config_has_required_keys(self):
        for template_id, template in TEMPLATES.items():
            wc = template.default_widget_config
            assert "welcome_message" in wc, f"{template_id}: missing welcome_message"
            assert "suggested_questions" in wc, f"{template_id}: missing suggested_questions"
            assert "theme" in wc, f"{template_id}: missing theme"
            assert "accent_color" in wc, f"{template_id}: missing accent_color"


class TestRenderSystemPrompt:
    def test_render_with_defaults(self):
        template = get_template("customer_service")
        rendered = render_system_prompt(template)
        assert "our company" in rendered
        assert template.suggested_tone in rendered
        assert "{company_name}" not in rendered
        assert "{tone}" not in rendered

    def test_render_with_custom_values(self):
        template = get_template("customer_service")
        rendered = render_system_prompt(template, company_name="Acme Corp", tone="formal and professional")
        assert "Acme Corp" in rendered
        assert "formal and professional" in rendered

    def test_render_all_templates(self):
        """Ensure all templates render without errors."""
        for template_id, template in TEMPLATES.items():
            rendered = render_system_prompt(template, company_name="TestCo", tone="friendly")
            assert "TestCo" in rendered
            assert "friendly" in rendered


# ─── Model Selection Tests ───


class TestModelRecommendation:
    """Test auto model selection with various provider combinations."""

    @pytest.mark.asyncio
    async def test_gcp_only(self):
        """GCP-only org should get Gemini models."""
        db = AsyncMock()
        # Mock the query result
        mock_result = MagicMock()
        mock_result.all.return_value = [("gcp",)]
        db.execute.return_value = mock_result

        rec = await recommend_models(db, uuid.uuid4())
        assert rec.primary["provider"] == "gcp"
        assert rec.primary["model_id"] == "gemini-2.0-flash"
        assert rec.fallback["provider"] == "gcp"
        assert rec.fallback["model_id"] == "gemini-2.5-flash"

    @pytest.mark.asyncio
    async def test_aws_only(self):
        """AWS-only org should get Nova models."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("aws",)]
        db.execute.return_value = mock_result

        rec = await recommend_models(db, uuid.uuid4())
        assert rec.primary["provider"] == "aws"
        assert "nova" in rec.primary["model_id"].lower()
        assert rec.fallback["provider"] == "aws"

    @pytest.mark.asyncio
    async def test_azure_only(self):
        """Azure-only org should get GPT models."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("azure",)]
        db.execute.return_value = mock_result

        rec = await recommend_models(db, uuid.uuid4())
        assert rec.primary["provider"] == "azure"
        assert "gpt" in rec.primary["model_id"].lower()
        assert rec.fallback["provider"] == "azure"
        assert rec.fallback["model_id"] == "gpt-4o"

    @pytest.mark.asyncio
    async def test_multi_cloud_picks_cheapest_primary(self):
        """Multi-cloud should pick cheapest for primary, strongest for fallback."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("gcp",), ("aws",), ("azure",)]
        db.execute.return_value = mock_result

        rec = await recommend_models(db, uuid.uuid4())
        # GCP Gemini 2.0 Flash has cost_rank=1 (cheapest)
        assert rec.primary["cost_rank"] == 1
        assert rec.primary["provider"] == "gcp"
        # Azure GPT-4o has cost_rank=5 (strongest)
        assert rec.fallback["cost_rank"] == 5
        assert rec.fallback["provider"] == "azure"

    @pytest.mark.asyncio
    async def test_no_providers(self):
        """No connected providers should default to GCP."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute.return_value = mock_result

        rec = await recommend_models(db, uuid.uuid4())
        assert rec.primary["provider"] == "gcp"
        assert rec.providers == []

    @pytest.mark.asyncio
    async def test_gcp_aws_multi_cloud(self):
        """GCP+AWS should pick GCP for primary (cheaper), AWS for fallback."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [("gcp",), ("aws",)]
        db.execute.return_value = mock_result

        rec = await recommend_models(db, uuid.uuid4())
        assert rec.primary["provider"] == "gcp"
        # AWS Nova Pro has cost_rank=4, GCP Gemini 2.5 Flash has cost_rank=3
        # Fallback should be the max cost_rank across all providers
        assert rec.fallback["cost_rank"] >= rec.primary["cost_rank"]

    @pytest.mark.asyncio
    async def test_recommendation_to_dict(self):
        rec = ModelRecommendation(
            primary=MODEL_CATALOG["gcp"]["primary"],
            fallback=MODEL_CATALOG["gcp"]["fallback"],
            providers=["gcp"],
        )
        d = rec.to_dict()
        assert "primary" in d
        assert "fallback" in d
        assert "providers" in d
        assert d["providers"] == ["gcp"]


# ─── Deploy Flow Tests ───


class TestDeployFlow:
    """Test that deploy creates agent with correct config."""

    @pytest.mark.asyncio
    async def test_deploy_creates_agent(self):
        """Deploy should create an agent with template defaults + customizations."""
        db = AsyncMock()

        # Mock project lookup
        mock_project = MagicMock()
        mock_project.id = uuid.uuid4()
        mock_project.org_id = uuid.uuid4()

        # First call: project lookup, second: provider lookup
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = mock_project

        provider_result = MagicMock()
        provider_result.all.return_value = [("gcp",)]

        db.execute.side_effect = [project_result, provider_result]

        # Mock agent creation
        mock_agent = MagicMock()
        mock_agent.id = uuid.uuid4()
        mock_agent.name = "Test Support Bot"
        mock_agent.model_id = "gemini-2.0-flash"
        mock_agent.bonbon_template_id = "customer_service"
        mock_agent.widget_enabled = True
        db.refresh = AsyncMock(return_value=None)
        db.commit = AsyncMock(return_value=None)

        # Patch Agent constructor to return our mock
        with patch("app.services.bonbon_deploy.Agent", return_value=mock_agent):
            result = await deploy_solution_kit(
                db=db,
                org_id=mock_project.org_id,
                request=DeployRequest(
                    template_id="customer_service",
                    project_id=mock_project.id,
                    name="Test Support Bot",
                    company_name="Acme Corp",
                    tone="warm and professional",
                    industry="Technology",
                ),
            )

        assert result.template_id == "customer_service"
        assert result.agent.name == "Test Support Bot"
        db.add.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_deploy_invalid_template(self):
        """Deploy with invalid template should raise ValueError."""
        db = AsyncMock()

        with pytest.raises(ValueError, match="Unknown template"):
            await deploy_solution_kit(
                db=db,
                org_id=uuid.uuid4(),
                request=DeployRequest(
                    template_id="nonexistent",
                    project_id=uuid.uuid4(),
                ),
            )

    @pytest.mark.asyncio
    async def test_deploy_invalid_project(self):
        """Deploy with non-existent project should raise ValueError."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Project not found"):
            await deploy_solution_kit(
                db=db,
                org_id=uuid.uuid4(),
                request=DeployRequest(
                    template_id="customer_service",
                    project_id=uuid.uuid4(),
                ),
            )


# ─── Widget Tests ───


class TestWidgetEndpoints:
    """Test widget config and chat endpoints."""

    def test_rate_limiter(self):
        """Test the in-memory rate limiter."""
        from app.api.routes.widget import _check_rate_limit, _rate_limit_store, RATE_LIMIT_RPM

        # Clear state
        test_ip = "test_ip_" + str(uuid.uuid4())

        # Should allow up to RATE_LIMIT_RPM requests
        for i in range(RATE_LIMIT_RPM):
            assert _check_rate_limit(test_ip) is True

        # Next request should be denied
        assert _check_rate_limit(test_ip) is False

    def test_rate_limiter_different_ips(self):
        """Different IPs should have independent limits."""
        from app.api.routes.widget import _check_rate_limit

        ip1 = "test_ip1_" + str(uuid.uuid4())
        ip2 = "test_ip2_" + str(uuid.uuid4())

        # Fill up ip1's limit
        for _ in range(20):
            _check_rate_limit(ip1)

        # ip2 should still be allowed
        assert _check_rate_limit(ip2) is True


# ─── Integration-style Tests (schemas/routes) ───


class TestBonBonSchemas:
    """Test that BonBon-related Pydantic schemas work correctly."""

    def test_agent_response_with_bonbon_fields(self):
        from app.schemas.bonobot import AgentResponse

        data = {
            "id": uuid.uuid4(),
            "project_id": uuid.uuid4(),
            "org_id": uuid.uuid4(),
            "group_id": None,
            "name": "Test Agent",
            "description": None,
            "system_prompt": "You are a test agent.",
            "model_id": "gemini-2.0-flash",
            "model_config": {},
            "knowledge_base_ids": [],
            "tool_policy": {"mode": "none", "allowed": [], "denied": [], "http_allowlist": []},
            "max_turns": 25,
            "timeout_seconds": 300,
            "compaction_enabled": True,
            "max_session_messages": 200,
            "rate_limit_rpm": 30,
            "budget_alert_threshold": Decimal("0.8"),
            "bonbon_template_id": "customer_service",
            "bonbon_config": {"tone": "warm", "company_name": "Acme"},
            "widget_enabled": True,
            "widget_config": {"welcome_message": "Hi!"},
            "status": "active",
            "last_active_at": None,
            "total_runs": 0,
            "total_tokens": 0,
            "total_cost": Decimal("0"),
            "created_at": "2026-02-26T00:00:00Z",
            "updated_at": "2026-02-26T00:00:00Z",
        }
        response = AgentResponse(**data)
        assert response.bonbon_template_id == "customer_service"
        assert response.widget_enabled is True
        assert response.bonbon_config["company_name"] == "Acme"

    def test_agent_response_without_bonbon_fields(self):
        """DIY agents should have None/False for BonBon fields."""
        from app.schemas.bonobot import AgentResponse

        data = {
            "id": uuid.uuid4(),
            "project_id": uuid.uuid4(),
            "org_id": uuid.uuid4(),
            "group_id": None,
            "name": "DIY Agent",
            "description": None,
            "system_prompt": "You are a custom agent.",
            "model_id": "gpt-4o",
            "model_config": {},
            "knowledge_base_ids": [],
            "tool_policy": {"mode": "none", "allowed": [], "denied": [], "http_allowlist": []},
            "max_turns": 25,
            "timeout_seconds": 300,
            "compaction_enabled": True,
            "max_session_messages": 200,
            "rate_limit_rpm": 30,
            "budget_alert_threshold": Decimal("0.8"),
            "status": "active",
            "last_active_at": None,
            "total_runs": 0,
            "total_tokens": 0,
            "total_cost": Decimal("0"),
            "created_at": "2026-02-26T00:00:00Z",
            "updated_at": "2026-02-26T00:00:00Z",
        }
        response = AgentResponse(**data)
        assert response.bonbon_template_id is None
        assert response.widget_enabled is False
        assert response.bonbon_config is None
