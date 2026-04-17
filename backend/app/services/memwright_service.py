"""Memwright conversational memory service for Bonito agents.

Provides per-session persistent memory using Memwright (SQLite + ChromaDB).
Designed as a lightweight, automatic memory layer that fires during agent
execution — recall before inference, store after response.

Key design decisions:
- Direct integration (not MCP) — platform controls when to recall/store
- Per-session isolation — different sessions never see each other's memories
- Model tier gating — small/fast models get zero budget to prevent hallucinations
- Non-fatal — all operations are wrapped in try/except, never blocks execution
"""

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Optional

from agent_memory import AgentMemory

logger = logging.getLogger(__name__)

# Default data directory (can override via MEMWRIGHT_DATA_DIR env var)
MEMWRIGHT_DATA_DIR = os.environ.get("MEMWRIGHT_DATA_DIR", "data/memwright")


class MemwrightService:
    """Manages per-session Memwright memory instances with model tier gating."""

    # Patterns for zero-budget models (fast/small — memory would cause hallucinations)
    ZERO_BUDGET_PATTERNS = ["flash", "mini", "kimi", "haiku", "gemma", "phi-"]
    # Default budget for models not matching any pattern
    DEFAULT_BUDGET = 500
    # Full budget for large/capable models
    FULL_BUDGET = 1000

    def __init__(self):
        self._instances: dict[str, AgentMemory] = {}
        Path(MEMWRIGHT_DATA_DIR).mkdir(parents=True, exist_ok=True)
        # Pre-warm sentence-transformers model at startup
        try:
            warmup_path = os.path.join(MEMWRIGHT_DATA_DIR, "_warmup")
            Path(warmup_path).mkdir(parents=True, exist_ok=True)
            warmup = AgentMemory(warmup_path)
            warmup.recall("warmup", budget=10)
            del warmup
            logger.info("Memwright sentence-transformers model pre-warmed")
        except Exception as e:
            logger.warning(f"Memwright pre-warm failed (non-fatal): {e}")

    def _get_budget(self, model_id: str) -> int:
        """Determine memory token budget based on model tier."""
        if not model_id or model_id == "auto":
            return 0  # auto-routed models are typically small/flash
        model_lower = model_id.lower()
        for pattern in self.ZERO_BUDGET_PATTERNS:
            if pattern in model_lower:
                return 0
        return self.FULL_BUDGET

    def _get_instance(self, session_id: str, agent_id: str, org_id: str) -> AgentMemory:
        """Get or create a Memwright instance for a specific session."""
        cache_key = f"{org_id}/{agent_id}/{session_id}"
        if cache_key not in self._instances:
            mem_path = os.path.join(MEMWRIGHT_DATA_DIR, org_id, agent_id, session_id)
            Path(mem_path).mkdir(parents=True, exist_ok=True)
            self._instances[cache_key] = AgentMemory(mem_path)
        return self._instances[cache_key]

    async def recall(
        self,
        session_id: str,
        agent_id: str,
        org_id: str,
        message: str,
        model_id: str,
    ) -> str:
        """Recall relevant memories for this session. Returns formatted context string."""
        budget = self._get_budget(model_id)
        if budget == 0:
            return ""

        try:
            mem = self._get_instance(session_id, agent_id, org_id)
            results = await asyncio.to_thread(mem.recall, message, budget=budget)
            if not results:
                return ""

            memory_lines = [r.memory.content for r in results]
            return (
                "[CONVERSATION MEMORY - Use this to resolve references like "
                '"this account", "the third one", "above", "that item", etc. '
                "This is what the user has been discussing.]\n"
                + "\n".join(memory_lines)
                + "\n[End of memory]"
            )
        except Exception as e:
            logger.warning(f"Memwright recall error (non-fatal): {e}")
            return ""

    async def store(
        self,
        session_id: str,
        agent_id: str,
        org_id: str,
        user_msg: str,
        assistant_msg: str,
        model_id: str,
        tags: Optional[list[str]] = None,
    ) -> None:
        """Store a conversation turn as memory."""
        budget = self._get_budget(model_id)
        if budget == 0:
            return

        try:
            mem = self._get_instance(session_id, agent_id, org_id)

            # Store user question + context
            await asyncio.to_thread(
                mem.add,
                f"User asked: {user_msg}",
                tags=tags or [],
                category="conversation",
                confidence=0.9,
            )

            # Store assistant response (truncated to key info)
            if assistant_msg and len(assistant_msg) > 20:
                summary = assistant_msg[:500]
                await asyncio.to_thread(
                    mem.add,
                    f"Assistant responded to '{user_msg[:100]}': {summary}",
                    tags=tags or [],
                    category="conversation",
                    confidence=0.8,
                )
        except Exception as e:
            logger.warning(f"Memwright store error (non-fatal): {e}")

    async def clear(self, session_id: str, agent_id: str, org_id: str) -> None:
        """Clear all memories for a session."""
        import shutil

        cache_key = f"{org_id}/{agent_id}/{session_id}"
        self._instances.pop(cache_key, None)
        mem_path = os.path.join(MEMWRIGHT_DATA_DIR, org_id, agent_id, session_id)
        try:
            if os.path.exists(mem_path):
                await asyncio.to_thread(shutil.rmtree, mem_path)
                logger.info(f"Cleared Memwright memory at {mem_path}")
        except Exception as e:
            logger.warning(f"Memwright clear error (non-fatal): {e}")
