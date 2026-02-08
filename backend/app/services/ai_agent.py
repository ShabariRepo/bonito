"""Bonito Copilot — Groq-powered AI agent for platform operations.

Org-aware agent that can query real data (costs, compliance, providers,
models) and stream responses via Groq's ultra-fast inference.
"""

import json
import logging
from datetime import date, timedelta
from typing import AsyncGenerator, Optional

from groq import AsyncGroq
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.cloud_provider import CloudProvider

logger = logging.getLogger(__name__)

COPILOT_SYSTEM_PROMPT = """You are **Bonito Copilot**, the AI operations assistant for the Bonito multi-cloud AI control plane.

You help enterprise teams manage AI workloads across AWS Bedrock, Azure AI Foundry, and Google Vertex AI.

## Your Personality
- Concise, direct, data-driven
- Use bullet points and bold for key numbers
- Always reference specific data when available
- Suggest actionable next steps
- You are NOT a general chatbot — you are a platform operations expert

## Your Capabilities
You can call tools to fetch real-time org data:
- Cost summaries and spending trends
- Compliance and governance status
- Provider health and connectivity
- Model recommendations (cheaper/better alternatives)
- Gateway usage statistics

## Response Guidelines
- Lead with the answer, then supporting data
- Format costs as currency ($X,XXX.XX)
- Flag anomalies or concerns proactively
- When suggesting optimizations, estimate savings
- Keep responses under 200 words unless detail is requested

## Current Context
{context}
"""

# Tool definitions for Groq function calling
COPILOT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_cost_summary",
            "description": "Get cost summary across all connected cloud providers for a given period",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly"],
                        "description": "Time period for cost aggregation",
                    }
                },
                "required": ["period"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_compliance_status",
            "description": "Get current compliance status across all frameworks and providers",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_provider_status",
            "description": "Get status and health of all connected cloud providers",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_model_recommendations",
            "description": "Get model recommendations — suggest cheaper or better alternatives based on current usage",
            "parameters": {
                "type": "object",
                "properties": {
                    "use_case": {
                        "type": "string",
                        "description": "Optional use case filter: text, code, vision, embeddings",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_usage_stats",
            "description": "Get API gateway usage statistics including request counts, latency, and error rates",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["1h", "24h", "7d", "30d"],
                        "description": "Time window for usage stats",
                    }
                },
            },
        },
    },
]


class BonitoCopilot:
    """Groq-powered copilot that understands the org's infrastructure."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self.model = "llama-3.3-70b-versatile"

    async def _build_context(self) -> str:
        """Build org context string for the system prompt."""
        parts = []

        # Connected providers
        try:
            result = await self.db.execute(
                select(CloudProvider).where(CloudProvider.status == "active")
            )
            providers = result.scalars().all()
            if providers:
                provider_lines = []
                for p in providers:
                    provider_lines.append(
                        f"  - {p.provider_type.upper()}: {p.name} (region: {p.region or 'default'}, status: {p.status})"
                    )
                parts.append("**Connected Providers:**\n" + "\n".join(provider_lines))
            else:
                parts.append("**Connected Providers:** None connected yet")
        except Exception as e:
            logger.warning(f"Failed to fetch providers for context: {e}")
            parts.append("**Connected Providers:** Unable to fetch")

        # Provider count summary
        try:
            result = await self.db.execute(
                select(
                    CloudProvider.provider_type,
                    func.count(CloudProvider.id),
                ).group_by(CloudProvider.provider_type)
            )
            counts = {row[0]: row[1] for row in result.all()}
            if counts:
                parts.append(
                    f"**Provider Summary:** "
                    + ", ".join(f"{k.upper()}: {v}" for k, v in counts.items())
                )
        except Exception:
            pass

        return "\n".join(parts) if parts else "No org data available yet — providers need to be connected."

    async def _execute_tool(self, name: str, args: dict) -> str:
        """Execute a tool call and return JSON result."""
        try:
            if name == "get_cost_summary":
                return await self._tool_cost_summary(args.get("period", "monthly"))
            elif name == "get_compliance_status":
                return await self._tool_compliance_status()
            elif name == "get_provider_status":
                return await self._tool_provider_status()
            elif name == "get_model_recommendations":
                return await self._tool_model_recommendations(args.get("use_case"))
            elif name == "get_usage_stats":
                return await self._tool_usage_stats(args.get("period", "24h"))
            else:
                return json.dumps({"error": f"Unknown tool: {name}"})
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return json.dumps({"error": str(e)})

    async def _tool_cost_summary(self, period: str) -> str:
        """Pull cost data from connected providers."""
        try:
            from app.services.cost_service import get_cost_summary_real
            summary = await get_cost_summary_real(period, self.db)
            return json.dumps({
                "period": period,
                "total_cost": summary.total_cost,
                "previous_period_cost": summary.previous_period_cost,
                "change_percent": summary.change_percent,
                "budget": summary.budget,
                "budget_used_percent": summary.budget_used_percent,
                "by_provider": [
                    {"provider": b.provider, "cost": b.cost, "percent": b.percent}
                    for b in (summary.by_provider or [])
                ],
            }, default=str)
        except Exception as e:
            return json.dumps({"error": f"Cost data unavailable: {e}", "hint": "Connect a cloud provider to see real cost data."})

    async def _tool_compliance_status(self) -> str:
        """Pull compliance check results."""
        try:
            from app.services.compliance_service import run_compliance_checks
            results = await run_compliance_checks(self.db)
            return json.dumps({
                "overall_score": results.overall_score,
                "status": results.status,
                "total_checks": results.total_checks,
                "passed": results.passed,
                "failed": results.failed,
                "warnings": results.warnings,
                "frameworks": [
                    {"name": f.name, "score": f.score, "status": f.status}
                    for f in (results.frameworks or [])
                ],
            }, default=str)
        except Exception as e:
            return json.dumps({"error": f"Compliance data unavailable: {e}", "hint": "Connect a cloud provider to run compliance checks."})

    async def _tool_provider_status(self) -> str:
        """Get provider connectivity and health."""
        try:
            result = await self.db.execute(select(CloudProvider))
            providers = result.scalars().all()
            return json.dumps({
                "providers": [
                    {
                        "name": p.name,
                        "type": p.provider_type,
                        "status": p.status,
                        "region": p.region,
                        "created_at": str(p.created_at) if hasattr(p, "created_at") else None,
                    }
                    for p in providers
                ],
                "total": len(providers),
                "active": sum(1 for p in providers if p.status == "active"),
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    async def _tool_model_recommendations(self, use_case: Optional[str] = None) -> str:
        """Suggest optimal models based on use case and pricing."""
        from app.services.provider_service import AZURE_MODELS, GCP_MODELS

        all_models = list(AZURE_MODELS) + list(GCP_MODELS)

        # Try to get AWS models from connected provider
        try:
            result = await self.db.execute(
                select(CloudProvider).where(
                    CloudProvider.provider_type == "aws",
                    CloudProvider.status == "active",
                )
            )
            aws = result.scalars().first()
            if aws:
                from app.services.provider_service import get_aws_provider
                aws_provider = await get_aws_provider(str(aws.id))
                aws_models = await aws_provider.list_models()
                all_models.extend(aws_models)
        except Exception:
            pass

        if use_case:
            all_models = [m for m in all_models if use_case.lower() in (m.capabilities if hasattr(m, "capabilities") else [])]

        # Sort by input price
        all_models.sort(key=lambda m: m.input_price_per_1k if hasattr(m, "input_price_per_1k") else 999)

        recommendations = []
        for m in all_models[:10]:
            recommendations.append({
                "name": m.name,
                "provider": m.provider,
                "input_price_per_1k": m.input_price_per_1k if hasattr(m, "input_price_per_1k") else None,
                "output_price_per_1k": m.output_price_per_1k if hasattr(m, "output_price_per_1k") else None,
                "capabilities": m.capabilities if hasattr(m, "capabilities") else [],
                "context_window": m.context_window if hasattr(m, "context_window") else None,
            })

        return json.dumps({
            "use_case": use_case or "all",
            "recommendations": recommendations,
            "tip": "Models sorted by input price. Consider context window and capabilities for your use case.",
        })

    async def _tool_usage_stats(self, period: str) -> str:
        """Get gateway usage stats from Redis."""
        try:
            from app.core.redis import redis_client
            stats_raw = await redis_client.get(f"gateway:stats:{period}")
            if stats_raw:
                return stats_raw
            return json.dumps({
                "period": period,
                "total_requests": 0,
                "avg_latency_ms": 0,
                "error_rate": 0,
                "hint": "No gateway usage data yet. The API gateway needs to be active.",
            })
        except Exception as e:
            return json.dumps({"error": str(e), "hint": "Gateway stats unavailable."})

    async def chat(self, message: str, history: list[dict] = None) -> dict:
        """Non-streaming chat — returns full response."""
        context = await self._build_context()
        system = COPILOT_SYSTEM_PROMPT.format(context=context)

        messages = [{"role": "system", "content": system}]
        if history:
            for h in history[-20:]:
                messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})

        # First call — may request tool use
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=COPILOT_TOOLS,
            tool_choice="auto",
            temperature=0.3,
            max_tokens=2048,
        )

        choice = response.choices[0]

        # Handle tool calls (single round)
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            messages.append(choice.message)
            for tc in choice.message.tool_calls:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                result = await self._execute_tool(tc.function.name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            # Second call with tool results
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )
            choice = response.choices[0]

        return {
            "message": choice.message.content or "",
            "model": self.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        }

    async def chat_stream(
        self, message: str, history: list[dict] = None
    ) -> AsyncGenerator[str, None]:
        """Streaming chat — yields SSE-formatted chunks.

        Handles tool calls in a non-streaming first pass, then streams
        the final response.
        """
        context = await self._build_context()
        system = COPILOT_SYSTEM_PROMPT.format(context=context)

        messages = [{"role": "system", "content": system}]
        if history:
            for h in history[-20:]:
                messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})

        # First pass: check for tool calls (non-streaming)
        first = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=COPILOT_TOOLS,
            tool_choice="auto",
            temperature=0.3,
            max_tokens=2048,
        )

        first_choice = first.choices[0]

        if first_choice.finish_reason == "tool_calls" and first_choice.message.tool_calls:
            # Execute tools
            messages.append(first_choice.message)
            tool_names = []
            for tc in first_choice.message.tool_calls:
                tool_names.append(tc.function.name)
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                result = await self._execute_tool(tc.function.name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            # Signal which tools were used
            yield f"data: {json.dumps({'type': 'tools', 'tools': tool_names})}\n\n"

        # Stream final response
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield f"data: {json.dumps({'type': 'content', 'text': delta.content})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    async def get_suggestions(self) -> list[dict]:
        """Generate proactive suggestions based on org state."""
        suggestions = []

        # Check if any providers connected
        try:
            result = await self.db.execute(
                select(func.count(CloudProvider.id)).where(CloudProvider.status == "active")
            )
            active_count = result.scalar() or 0

            if active_count == 0:
                suggestions.append({
                    "type": "setup",
                    "title": "Connect a cloud provider",
                    "description": "Connect AWS, Azure, or GCP to start managing AI workloads",
                    "action": "/providers",
                    "priority": "high",
                })
            else:
                suggestions.append({
                    "type": "cost",
                    "title": "Review this month's spending",
                    "description": f"You have {active_count} active provider(s). Check your cost trends.",
                    "query": "What's our spend this month?",
                    "priority": "medium",
                })
                suggestions.append({
                    "type": "compliance",
                    "title": "Run a compliance check",
                    "description": "Verify your infrastructure meets governance requirements",
                    "query": "What's our compliance status?",
                    "priority": "medium",
                })
                suggestions.append({
                    "type": "optimization",
                    "title": "Find cost savings",
                    "description": "Get model recommendations to reduce spending",
                    "query": "How can we optimize our AI spending?",
                    "priority": "low",
                })
        except Exception as e:
            logger.warning(f"Failed to generate suggestions: {e}")
            suggestions.append({
                "type": "general",
                "title": "Ask me anything",
                "description": "I can help with costs, compliance, models, and more",
                "query": "What can you help me with?",
                "priority": "low",
            })

        return suggestions
