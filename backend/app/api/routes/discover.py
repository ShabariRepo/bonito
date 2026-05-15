"""
Discover API Routes

Public-facing endpoint that researches a company and generates
personalised Bonito use cases.  No auth required.
"""

import json
import time
import uuid
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status, Depends
from pydantic import BaseModel, Field

from app.core.config import settings

router = APIRouter(prefix="/discover", tags=["discover"])


# ─── Rate limiter (5 req/min — tighter than widget) ───

_rate_store: Dict[str, list] = defaultdict(list)
RATE_LIMIT_RPM = 5
RATE_LIMIT_WINDOW = 60


def _check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW
    _rate_store[client_ip] = [t for t in _rate_store[client_ip] if t > cutoff]
    if len(_rate_store[client_ip]) >= RATE_LIMIT_RPM:
        return False
    _rate_store[client_ip].append(now)
    return True


# ─── Schemas ───

class DiscoverUseCase(BaseModel):
    title: str
    description: str
    bonito_features: List[str]
    impact: str


class DiscoverRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    website_url: Optional[str] = Field(None, max_length=500)


class DiscoverResponse(BaseModel):
    id: str
    company_name: str
    overview: str
    industry: str
    company_size: str
    challenges: List[str]
    use_cases: List[DiscoverUseCase]
    estimated_impact: str
    recommended_plan: str


# ─── System prompt ───

DISCOVER_SYSTEM_PROMPT = """You are Bonito's Discovery Analyst. Given a company name (and optionally their website URL), produce a detailed analysis of how Bonito's AI operations platform can help them.

## About Bonito
Bonito is an enterprise AI operations platform — a unified control plane for managing AI workloads across AWS Bedrock, Azure AI, Google Vertex AI, OpenAI, Anthropic, and Groq. Key capabilities:

- **Multi-cloud AI gateway**: Single OpenAI-compatible API endpoint that routes to any of 6 providers. One `bn-` API key replaces dozens of provider keys.
- **Intelligent failover**: Automatic retry across equivalent models on different providers when rate limits, timeouts, or 5xx errors hit. Zero-downtime AI.
- **Cost intelligence**: Real-time spend tracking per model, per team, per project. Forecasting and optimisation recommendations ("switch this workflow from GPT-4o to Claude Haiku, save 80%").
- **Smart routing**: 5 strategies — cost-optimised, latency-optimised, A/B testing, balanced, failover. Visual policy builder.
- **AI Agents (Bonobot)**: Deploy autonomous enterprise agents with a visual drag-and-drop canvas. Built-in tools: knowledge base search, HTTP requests, agent-to-agent orchestration, scheduled execution, human-in-the-loop approval queues.
- **Knowledge Base (RAG)**: Upload documents (PDF, DOCX, etc.), auto-chunk and embed with pgvector, semantic search. Agents and gateway queries pull relevant context automatically. Per-project isolation.
- **Compliance & governance**: SOC-2, HIPAA, GDPR policy checks across all providers. Full audit trail of every request.
- **SAML SSO**: Okta, Azure AD, Google Workspace. JIT provisioning, SSO enforcement.
- **Model playground**: Live testing with parameter tuning, side-by-side comparison of up to 4 models.
- **One-click model activation**: Enable models directly from Bonito UI (Bedrock entitlements, Azure deployments, GCP API enable).

## Pricing
- Free: 3 providers, 25K requests/mo, 3 seats
- Pro ($999/mo): 5 providers, 500K requests/mo, unlimited seats, 5 agents, advanced routing, RAG, analytics
- Enterprise ($10K–$20K/mo): Unlimited everything, SSO/SAML, RBAC, compliance, 99.9% SLA

## Your Task
Research the company using your knowledge. Identify their industry, likely AI use cases, and specific pain points that Bonito solves. Be specific to the company — reference their actual products, services, or industry dynamics where possible. If you cannot confidently identify the company, still generate plausible use cases based on the name, URL, and any context clues.

## Response Format
Respond with ONLY valid JSON (no markdown, no code fences, no commentary):
{
  "overview": "2-3 sentence company description",
  "industry": "Primary industry category",
  "company_size": "startup | mid-market | enterprise",
  "challenges": ["3-4 industry-specific AI challenges this company likely faces"],
  "use_cases": [
    {
      "title": "Specific use case name",
      "description": "2-3 sentences on how this applies to the company specifically. Be concrete.",
      "bonito_features": ["Gateway", "Cost Intelligence", etc.],
      "impact": "Quantified or qualified expected impact"
    }
  ],
  "estimated_impact": "1-2 sentence overall ROI summary for this specific company",
  "recommended_plan": "free|pro|enterprise"
}

Generate 4-5 use cases. Be specific, not generic. Make the company feel like you actually understand their business."""


# ─── Helpers ───

def _parse_llm_json(text: str) -> dict:
    """Parse JSON from LLM response, stripping code fences if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove opening fence (with optional language tag)
        first_newline = cleaned.index("\n")
        cleaned = cleaned[first_newline + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return json.loads(cleaned.strip())


async def _call_llm(company_name: str, website_url: Optional[str]) -> dict:
    """Call Groq (or fallback) via litellm to generate the discovery report."""
    import litellm

    user_msg = f"Company: {company_name}"
    if website_url:
        user_msg += f"\nWebsite: {website_url}"

    api_key = settings.groq_api_key
    model = "groq/llama-3.3-70b-versatile"

    if not api_key:
        # Fallback to OpenAI if Groq key isn't set
        api_key = getattr(settings, "openai_api_key", None)
        model = "gpt-4o-mini"

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Discovery service is temporarily unavailable.",
        )

    response = await litellm.acompletion(
        model=model,
        api_key=api_key,
        messages=[
            {"role": "system", "content": DISCOVER_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.5,
        max_tokens=2048,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    return _parse_llm_json(raw)


async def _store_result(result_id: str, data: dict, ttl: int = 604800):
    """Cache result in Redis for 7 days. Silently skip if Redis unavailable."""
    try:
        from app.core.redis import get_redis
        redis = await get_redis()
        if redis:
            await redis.set(f"discover:{result_id}", json.dumps(data), ex=ttl)
    except Exception:
        pass


async def _fetch_result(result_id: str) -> Optional[dict]:
    """Fetch cached result from Redis."""
    try:
        from app.core.redis import get_redis
        redis = await get_redis()
        if redis:
            raw = await redis.get(f"discover:{result_id}")
            if raw:
                return json.loads(raw)
    except Exception:
        pass
    return None


# ─── Routes ───

@router.post("", response_model=DiscoverResponse)
async def discover_company(
    body: DiscoverRequest,
    request: Request,
):
    """
    Analyse a company and generate personalised Bonito use cases.
    PUBLIC endpoint — rate-limited to 5 req/min per IP.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a moment before trying again.",
        )

    try:
        data = await _call_llm(body.company_name, body.website_url)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate analysis. Please try again.",
        )

    result_id = str(uuid.uuid4())

    response_data = {
        "id": result_id,
        "company_name": body.company_name,
        "overview": data.get("overview", ""),
        "industry": data.get("industry", "Technology"),
        "company_size": data.get("company_size", "mid-market"),
        "challenges": data.get("challenges", []),
        "use_cases": data.get("use_cases", []),
        "estimated_impact": data.get("estimated_impact", ""),
        "recommended_plan": data.get("recommended_plan", "pro"),
    }

    # Cache for shareable link
    await _store_result(result_id, response_data)

    return DiscoverResponse(**response_data)


@router.get("/{result_id}", response_model=DiscoverResponse)
async def get_discover_result(result_id: str):
    """
    Fetch a previously generated discovery report by ID.
    PUBLIC endpoint for shareable links.
    """
    try:
        uuid.UUID(result_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid result ID",
        )

    data = await _fetch_result(result_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or expired. Generate a new one.",
        )

    return DiscoverResponse(**data)
