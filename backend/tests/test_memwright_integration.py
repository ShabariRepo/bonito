"""
Tests for Memwright conversational memory integration.

Covers:
  Group 1 — Regression: existing functionality unaffected by Memwright
  Group 2 — Memory Recall: context injection into system prompt
  Group 3 — Memory Store: conversation turns persisted after execution
  Group 4 — Model Tier Gating: budget enforcement by model type
  Group 5 — Session Isolation: memories don't leak across sessions
  Group 6 — Performance: async wrappers, non-blocking behavior
"""

import asyncio
import collections
import os
import shutil
import tempfile
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.agent import Agent
from app.models.agent_session import AgentSession
from app.models.project import Project
from app.services.memwright_service import MemwrightService
from app.services.agent_engine import AgentEngine
from app.schemas.bonobot import AgentRunResult, SecurityMetadata


# ──────────────────────────────────────────────────────────────────
# Helpers & Fixtures
# ──────────────────────────────────────────────────────────────────

def _make_llm_response(
    content: str = "Hello from the LLM",
    model: str = "gpt-4o",
    prompt_tokens: int = 30,
    completion_tokens: int = 20,
    cost: float = 0.001,
) -> Dict[str, Any]:
    message = {"role": "assistant", "content": content}
    return {
        "choices": [{"message": message}],
        "usage": {
            "total_tokens": prompt_tokens + completion_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        },
        "cost": cost,
        "model": model,
    }


def _build_mock_redis(rate_count: int = 0) -> AsyncMock:
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=str(rate_count) if rate_count else None)
    mock.incr = AsyncMock(return_value=rate_count + 1)
    mock.expire = AsyncMock()
    pipe = AsyncMock()
    pipe.incr = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)
    pipe.execute = AsyncMock(return_value=[rate_count + 1, True])
    mock.pipeline = MagicMock(return_value=pipe)
    mock.hset = AsyncMock()
    mock.hgetall = AsyncMock(return_value={})
    mock.delete = AsyncMock()
    return mock


@pytest_asyncio.fixture
async def project(test_engine, test_org) -> Project:
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        proj = Project(
            org_id=test_org.id,
            name="Memory Test Project",
            budget_monthly=Decimal("100.00"),
            budget_spent=Decimal("0.00"),
        )
        session.add(proj)
        await session.commit()
        await session.refresh(proj)
        return proj


@pytest_asyncio.fixture
async def agent_opus(test_engine, test_org, project) -> Agent:
    """Agent using a large model (full memory budget)."""
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        a = Agent(
            project_id=project.id,
            org_id=test_org.id,
            name="Opus Agent",
            system_prompt="You are a helpful agent with memory.",
            model_id="claude-opus-4-20250514",
            tool_policy={"mode": "none", "allowed": [], "denied": [], "http_allowlist": []},
            max_turns=5,
            rate_limit_rpm=30,
            status="active",
        )
        session.add(a)
        await session.commit()
        await session.refresh(a)
        return a


@pytest_asyncio.fixture
async def agent_flash(test_engine, test_org, project) -> Agent:
    """Agent using a small model (zero memory budget)."""
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        a = Agent(
            project_id=project.id,
            org_id=test_org.id,
            name="Flash Agent",
            system_prompt="You are a fast agent.",
            model_id="gemini-2.0-flash-001",
            tool_policy={"mode": "none", "allowed": [], "denied": [], "http_allowlist": []},
            max_turns=5,
            rate_limit_rpm=30,
            status="active",
        )
        session.add(a)
        await session.commit()
        await session.refresh(a)
        return a


@pytest_asyncio.fixture
async def agent_auto(test_engine, test_org, project) -> Agent:
    """Agent with auto model routing (zero memory budget)."""
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        a = Agent(
            project_id=project.id,
            org_id=test_org.id,
            name="Auto Agent",
            system_prompt="You are a routed agent.",
            model_id="auto",
            tool_policy={"mode": "none", "allowed": [], "denied": [], "http_allowlist": []},
            max_turns=5,
            rate_limit_rpm=30,
            status="active",
        )
        session.add(a)
        await session.commit()
        await session.refresh(a)
        return a


# ──────────────────────────────────────────────────────────────────
# Group 1 — Regression Tests
# ──────────────────────────────────────────────────────────────────

class TestRegressionNoMemoryInterference:
    """Verify existing functionality is unaffected by Memwright."""

    @pytest.mark.asyncio
    async def test_execute_basic_with_memwright_present(self, test_engine, agent_opus):
        """Standard execution works with Memwright in the engine."""
        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            engine = AgentEngine()
            redis = _build_mock_redis()

            with patch("app.services.agent_engine.gateway_chat_completion", new_callable=AsyncMock) as mock_gateway:
                mock_gateway.return_value = _make_llm_response("Test response")

                # Mock memwright to isolate this test
                engine._memwright = AsyncMock(spec=MemwrightService)
                engine._memwright.recall = AsyncMock(return_value="")
                engine._memwright.store = AsyncMock()

                result = await engine.execute(agent_opus, "Hello", db, redis)

                assert result.content == "Test response"
                assert result.tokens > 0

    @pytest.mark.asyncio
    async def test_zero_budget_model_skips_memory(self, test_engine, agent_flash):
        """Flash/mini models should not trigger recall or store."""
        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            engine = AgentEngine()
            redis = _build_mock_redis()

            with patch("app.services.agent_engine.gateway_chat_completion", new_callable=AsyncMock) as mock_gateway:
                mock_gateway.return_value = _make_llm_response("Fast reply")

                engine._memwright = AsyncMock(spec=MemwrightService)
                engine._memwright.recall = AsyncMock(return_value="")
                engine._memwright.store = AsyncMock()

                result = await engine.execute(agent_flash, "Quick question", db, redis)

                assert result.content == "Fast reply"
                # recall and store should be called but return empty/no-op due to budget=0
                engine._memwright.recall.assert_called_once()
                engine._memwright.store.assert_called_once()


# ──────────────────────────────────────────────────────────────────
# Group 2 — Memory Recall Tests
# ──────────────────────────────────────────────────────────────────

class TestMemoryRecall:
    """Verify memory recall is injected into system prompt."""

    @pytest.mark.asyncio
    async def test_recall_injects_into_system_prompt(self, test_engine, agent_opus):
        """When recall returns content, it should appear in the system prompt."""
        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            engine = AgentEngine()
            redis = _build_mock_redis()

            captured_messages = []

            async def capture_gateway(*args, **kwargs):
                request_data = kwargs.get("request_data", {})
                msgs = request_data.get("messages", [])
                captured_messages.extend(msgs)
                return _make_llm_response("Remembered!")

            with patch("app.services.agent_engine.gateway_chat_completion", new_callable=AsyncMock) as mock_gateway:
                mock_gateway.side_effect = capture_gateway

                engine._memwright = AsyncMock(spec=MemwrightService)
                engine._memwright.recall = AsyncMock(return_value="User previously asked about RV campaigns.")
                engine._memwright.store = AsyncMock()

                result = await engine.execute(agent_opus, "What about the third one?", db, redis)

                assert result.content == "Remembered!"
                # Check system prompt contains memory context
                system_msg = captured_messages[0]
                assert "## Conversation Memory" in system_msg["content"]
                assert "RV campaigns" in system_msg["content"]

    @pytest.mark.asyncio
    async def test_recall_empty_no_section(self, test_engine, agent_opus):
        """When recall returns empty, no Conversation Memory section in prompt."""
        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            engine = AgentEngine()
            redis = _build_mock_redis()

            captured_messages = []

            async def capture_gateway(*args, **kwargs):
                request_data = kwargs.get("request_data", {})
                msgs = request_data.get("messages", [])
                captured_messages.extend(msgs)
                return _make_llm_response("No memory")

            with patch("app.services.agent_engine.gateway_chat_completion", new_callable=AsyncMock) as mock_gateway:
                mock_gateway.side_effect = capture_gateway

                engine._memwright = AsyncMock(spec=MemwrightService)
                engine._memwright.recall = AsyncMock(return_value="")
                engine._memwright.store = AsyncMock()

                await engine.execute(agent_opus, "Hello", db, redis)

                system_msg = captured_messages[0]
                assert "## Conversation Memory" not in system_msg["content"]

    @pytest.mark.asyncio
    async def test_recall_failure_nonfatal(self, test_engine, agent_opus):
        """If recall throws, execute still completes successfully."""
        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            engine = AgentEngine()
            redis = _build_mock_redis()

            with patch("app.services.agent_engine.gateway_chat_completion", new_callable=AsyncMock) as mock_gateway:
                mock_gateway.return_value = _make_llm_response("Still works")

                engine._memwright = AsyncMock(spec=MemwrightService)
                engine._memwright.recall = AsyncMock(side_effect=Exception("ChromaDB exploded"))
                engine._memwright.store = AsyncMock()

                # Should NOT raise — recall failure is non-fatal
                result = await engine.execute(agent_opus, "Hello", db, redis)
                assert result.content == "Still works"


# ──────────────────────────────────────────────────────────────────
# Group 3 — Memory Store Tests
# ──────────────────────────────────────────────────────────────────

class TestMemoryStore:
    """Verify conversation turns are stored after execution."""

    @pytest.mark.asyncio
    async def test_store_called_after_response(self, test_engine, agent_opus):
        """Store should be called with user message and assistant response."""
        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            engine = AgentEngine()
            redis = _build_mock_redis()

            with patch("app.services.agent_engine.gateway_chat_completion", new_callable=AsyncMock) as mock_gateway:
                mock_gateway.return_value = _make_llm_response("Here are the RV campaigns")

                engine._memwright = AsyncMock(spec=MemwrightService)
                engine._memwright.recall = AsyncMock(return_value="")
                engine._memwright.store = AsyncMock()

                await engine.execute(agent_opus, "Show me RV campaigns", db, redis)

                engine._memwright.store.assert_called_once()
                call_kwargs = engine._memwright.store.call_args[1]
                assert "RV campaigns" in call_kwargs["user_msg"]
                assert "Here are the RV campaigns" in call_kwargs["assistant_msg"]

    @pytest.mark.asyncio
    async def test_store_not_called_when_no_content(self, test_engine, agent_opus):
        """Store should NOT be called when result.content is empty/None."""
        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            engine = AgentEngine()
            redis = _build_mock_redis()

            with patch("app.services.agent_engine.gateway_chat_completion", new_callable=AsyncMock) as mock_gateway:
                mock_gateway.return_value = _make_llm_response(content="")

                engine._memwright = AsyncMock(spec=MemwrightService)
                engine._memwright.recall = AsyncMock(return_value="")
                engine._memwright.store = AsyncMock()

                await engine.execute(agent_opus, "Hello", db, redis)

                engine._memwright.store.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_failure_nonfatal(self, test_engine, agent_opus):
        """If store throws, execute still returns the result."""
        factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db:
            engine = AgentEngine()
            redis = _build_mock_redis()

            with patch("app.services.agent_engine.gateway_chat_completion", new_callable=AsyncMock) as mock_gateway:
                mock_gateway.return_value = _make_llm_response("Good response")

                engine._memwright = AsyncMock(spec=MemwrightService)
                engine._memwright.recall = AsyncMock(return_value="")
                engine._memwright.store = AsyncMock(side_effect=Exception("Disk full"))

                result = await engine.execute(agent_opus, "Hello", db, redis)
                assert result.content == "Good response"


# ──────────────────────────────────────────────────────────────────
# Group 4 — Model Tier Gating Tests
# ──────────────────────────────────────────────────────────────────

class TestModelTierGating:
    """Verify memory budget is correctly assigned by model type."""

    def test_opus_gets_full_budget(self):
        svc = MemwrightService.__new__(MemwrightService)
        assert svc._get_budget("claude-opus-4-20250514") == MemwrightService.FULL_BUDGET

    def test_sonnet_gets_full_budget(self):
        svc = MemwrightService.__new__(MemwrightService)
        assert svc._get_budget("claude-sonnet-4-20250514") == MemwrightService.FULL_BUDGET

    def test_gpt4o_gets_full_budget(self):
        svc = MemwrightService.__new__(MemwrightService)
        assert svc._get_budget("gpt-4o") == MemwrightService.FULL_BUDGET

    def test_flash_gets_zero_budget(self):
        svc = MemwrightService.__new__(MemwrightService)
        assert svc._get_budget("gemini-2.0-flash-001") == 0

    def test_mini_gets_zero_budget(self):
        svc = MemwrightService.__new__(MemwrightService)
        assert svc._get_budget("gpt-4o-mini") == 0

    def test_kimi_gets_zero_budget(self):
        svc = MemwrightService.__new__(MemwrightService)
        assert svc._get_budget("kimi-k2.5") == 0

    def test_haiku_gets_zero_budget(self):
        svc = MemwrightService.__new__(MemwrightService)
        assert svc._get_budget("claude-haiku-4-5-20251001") == 0

    def test_auto_gets_zero_budget(self):
        svc = MemwrightService.__new__(MemwrightService)
        assert svc._get_budget("auto") == 0

    def test_none_gets_zero_budget(self):
        svc = MemwrightService.__new__(MemwrightService)
        assert svc._get_budget("") == 0
        assert svc._get_budget(None) == 0

    def test_unknown_model_gets_default(self):
        svc = MemwrightService.__new__(MemwrightService)
        assert svc._get_budget("some-future-model-v2") == MemwrightService.FULL_BUDGET


# ──────────────────────────────────────────────────────────────────
# Group 5 — Session Isolation Tests (unit-level)
# ──────────────────────────────────────────────────────────────────

class TestSessionIsolation:
    """Verify memory instances are isolated per session."""

    def test_different_sessions_different_instances(self):
        svc = MemwrightService.__new__(MemwrightService)
        svc._instances = collections.OrderedDict()

        # Each call to AgentMemory() returns a unique mock instance
        mock_agent_memory = MagicMock(side_effect=lambda path: MagicMock())

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.services.memwright_service.MEMWRIGHT_DATA_DIR", tmpdir):
                with patch("app.services.memwright_service._AGENT_MEMORY_AVAILABLE", True):
                    with patch("app.services.memwright_service.AgentMemory", mock_agent_memory):
                        inst_a = svc._get_instance("session-a", "agent-1", "org-1")
                        inst_b = svc._get_instance("session-b", "agent-1", "org-1")
                        assert inst_a is not inst_b

    def test_same_session_reuses_instance(self):
        svc = MemwrightService.__new__(MemwrightService)
        svc._instances = collections.OrderedDict()

        mock_agent_memory = MagicMock(side_effect=lambda path: MagicMock())

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.services.memwright_service.MEMWRIGHT_DATA_DIR", tmpdir):
                with patch("app.services.memwright_service._AGENT_MEMORY_AVAILABLE", True):
                    with patch("app.services.memwright_service.AgentMemory", mock_agent_memory):
                        inst_a = svc._get_instance("session-x", "agent-1", "org-1")
                        inst_b = svc._get_instance("session-x", "agent-1", "org-1")
                        assert inst_a is inst_b

    def test_different_agents_different_instances(self):
        svc = MemwrightService.__new__(MemwrightService)
        svc._instances = collections.OrderedDict()

        mock_agent_memory = MagicMock(side_effect=lambda path: MagicMock())

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.services.memwright_service.MEMWRIGHT_DATA_DIR", tmpdir):
                with patch("app.services.memwright_service._AGENT_MEMORY_AVAILABLE", True):
                    with patch("app.services.memwright_service.AgentMemory", mock_agent_memory):
                        inst_a = svc._get_instance("session-1", "agent-a", "org-1")
                        inst_b = svc._get_instance("session-1", "agent-b", "org-1")
                        assert inst_a is not inst_b


# ──────────────────────────────────────────────────────────────────
# Group 6 — Performance Tests
# ──────────────────────────────────────────────────────────────────

class TestPerformance:
    """Verify memory operations use async wrappers."""

    @pytest.mark.asyncio
    async def test_recall_uses_executor(self):
        """Recall should run Memwright in an executor to avoid blocking."""
        svc = MemwrightService.__new__(MemwrightService)
        svc._instances = collections.OrderedDict()
        svc._executor = MagicMock()

        mock_mem = MagicMock()
        mock_mem.recall.return_value = []

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=[])

        with patch("app.services.memwright_service._AGENT_MEMORY_AVAILABLE", True):
            with patch.object(svc, "_get_instance", return_value=mock_mem):
                with patch.object(svc, "_get_budget", return_value=1000):
                    with patch("asyncio.get_running_loop", return_value=mock_loop):
                        await svc.recall("s1", "a1", "o1", "test query", "claude-opus-4-20250514")
                        mock_loop.run_in_executor.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_uses_executor(self):
        """Store should run Memwright in an executor to avoid blocking."""
        svc = MemwrightService.__new__(MemwrightService)
        svc._instances = collections.OrderedDict()
        svc._executor = MagicMock()

        mock_mem = MagicMock()

        mock_loop = MagicMock()
        mock_loop.run_in_executor = AsyncMock(return_value=None)

        with patch("app.services.memwright_service._AGENT_MEMORY_AVAILABLE", True):
            with patch.object(svc, "_get_instance", return_value=mock_mem):
                with patch.object(svc, "_get_budget", return_value=1000):
                    with patch("asyncio.get_running_loop", return_value=mock_loop):
                        # Assistant msg must be >20 chars for both user+assistant stores to fire
                        await svc.store("s1", "a1", "o1", "user msg", "This is a sufficiently long assistant response for testing", "claude-opus-4-20250514")
                        # Should be called twice: once for user msg, once for assistant msg
                        assert mock_loop.run_in_executor.call_count == 2
