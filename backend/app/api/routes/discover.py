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

from fastapi import APIRouter, HTTPException, Request, status
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
Bonito is a premium enterprise AI operations platform — a unified control plane for managing AI workloads across AWS Bedrock, Azure AI, Google Vertex AI, OpenAI, Anthropic, and Groq. Key capabilities:

- **Multi-cloud AI gateway**: Single OpenAI-compatible API endpoint that routes to any of 6 providers. One `bn-` API key replaces dozens of provider keys.
- **Intelligent failover**: Automatic retry across equivalent models on different providers when rate limits, timeouts, or 5xx errors hit. Zero-downtime AI.
- **Cost intelligence**: Real-time spend tracking per model, per team, per project. Forecasting and optimisation recommendations.
- **Smart routing**: 5 strategies — cost-optimised, latency-optimised, A/B testing, balanced, failover. Visual policy builder.
- **AI Agents (Bonobot)**: Deploy autonomous enterprise agents with a visual drag-and-drop canvas. Built-in tools: knowledge base search, HTTP requests, agent-to-agent orchestration, scheduled execution, human-in-the-loop approval queues.
- **Knowledge Base (RAG)**: Upload documents (PDF, DOCX, etc.), auto-chunk and embed with pgvector, semantic search. Agents and gateway queries pull relevant context automatically. Per-project isolation.
- **Compliance & governance**: SOC-2, HIPAA, GDPR policy checks across all providers. Full audit trail of every request.
- **SAML SSO**: Okta, Azure AD, Google Workspace. JIT provisioning, SSO enforcement.
- **Model playground**: Live testing with parameter tuning, side-by-side comparison of up to 4 models.
- **One-click model activation**: Enable models directly from Bonito UI (Bedrock entitlements, Azure deployments, GCP API enable).
- **White-label / embedded AI**: Bonito powers AI for other platforms behind the scenes. Companies embed Bonito's gateway and agent framework into their own products.

## What Companies Are Building on Bonito (Agent Examples)
Real companies use Bonito's agent framework to deploy production AI workflows:

- **Automotive marketplace**: Deployed AI agents for vehicle listing enrichment, dealer recommendation engines, and automated customer Q&A across thousands of dealership inventories. Agents pull from knowledge bases of vehicle specs and pricing data.
- **Furniture / interior design platform**: AI agents generate personalised room designs, product recommendations, and visual mockups. RAG pipeline pulls from product catalogues and design guidelines.
- **Restaurant chain operations**: AI agents handle menu optimisation, supply chain forecasting, and automated customer service across hundreds of locations. Scheduled agents run nightly analytics.
- **Creative agency / media production**: Multi-agent pipelines for campaign ideation, copy generation, asset production, and compliance review. Orchestrator agents coordinate specialist sub-agents.
- **Audio / communications platform**: AI agents for real-time transcription, conversation intelligence, and automated call summarisation routed through Bonito's multi-provider gateway for reliability.

These are not hypothetical — these are production deployments running through Bonito's gateway and agent framework today.

## Pricing
- Free: 3 providers, 25K requests/mo, 3 seats — for small teams exploring AI
- Pro ($999/mo): 5 providers, 500K requests/mo, unlimited seats, 5 agents, advanced routing, RAG, analytics
- Enterprise ($10K–$20K/mo): Unlimited everything, SSO/SAML, RBAC, compliance, 99.9% SLA, dedicated support
- Scale (Custom, $200K+/yr): Dedicated infrastructure, multi-region deployment, 99.99% SLA, custom fine-tuning pipeline, white-glove onboarding, dedicated account team

## CRITICAL: Plan Recommendation Rules
You MUST follow these rules when recommending a plan:
- **Enterprise or Scale** for ANY company that is publicly traded, has 500+ employees, is a household name, operates in multiple countries, or has annual revenue over $100M. These companies need SSO, RBAC, compliance, SLA guarantees, and dedicated support. Do NOT recommend Pro or Free for large companies — it would be insulting.
- **Scale** for Fortune 500 companies, companies with 5000+ employees, or companies where AI is core to their product.
- **Enterprise** for mid-to-large companies (200-5000 employees), well-funded startups ($50M+ raised), or companies in regulated industries (finance, healthcare, government).
- **Pro** for funded startups, growing mid-market companies (50-200 employees), or tech-forward SMBs.
- **Free** ONLY for very early-stage startups, solo developers, or teams just beginning to explore AI.

When in doubt, recommend HIGHER not lower. Bonito is a premium platform — position it accordingly.

## Your Task
Research the company using your knowledge. Identify their industry, likely AI use cases, and specific pain points that Bonito solves. Be specific to the company — reference their actual products, services, or industry dynamics where possible. Where relevant, draw parallels to the agent examples above to show what's possible. If you cannot confidently identify the company, still generate plausible use cases based on the name, URL, and any context clues.

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
      "description": "2-3 sentences on how this applies to the company specifically. Be concrete. Reference their actual products or services where possible.",
      "bonito_features": ["Gateway", "Cost Intelligence", etc.],
      "impact": "Quantified or qualified expected impact"
    }
  ],
  "estimated_impact": "1-2 sentence overall ROI summary for this specific company",
  "recommended_plan": "free|pro|enterprise|scale"
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


async def _scrape_website(url: str) -> Optional[str]:
    """Fetch website content for context. Returns plain text summary or None."""
    import httpx
    from html.parser import HTMLParser

    class _TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self._texts: list = []
            self._skip = False
            self._skip_tags = {"script", "style", "noscript", "svg", "path"}

        def handle_starttag(self, tag, attrs):
            if tag in self._skip_tags:
                self._skip = True

        def handle_endtag(self, tag):
            if tag in self._skip_tags:
                self._skip = False

        def handle_data(self, data):
            if not self._skip:
                text = data.strip()
                if text:
                    self._texts.append(text)

        def get_text(self) -> str:
            return "\n".join(self._texts)

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "BonitoDiscovery/1.0"})
            resp.raise_for_status()
            html = resp.text

        extractor = _TextExtractor()
        extractor.feed(html)
        text = extractor.get_text()
        # Limit to ~3000 chars to avoid blowing up context
        return text[:3000] if text else None
    except Exception:
        return None


async def _call_llm(company_name: str, website_url: Optional[str]) -> dict:
    """Call Groq (or fallback) via litellm to generate the discovery report."""
    import litellm

    user_msg = f"Company: {company_name}"
    if website_url:
        user_msg += f"\nWebsite: {website_url}"
        # Actually fetch the website so the LLM has real context
        site_content = await _scrape_website(website_url)
        if site_content:
            user_msg += f"\n\n--- Website Content ---\n{site_content}\n--- End Website Content ---"

    api_key = settings.groq_api_key
    model = "groq/llama-3.3-70b-versatile"

    if not api_key:
        # Fallback to OpenAI platform key if Groq key isn't set
        api_key = settings.platform_embedding_api_key
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
        max_tokens=3000,
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


async def _log_discover(result_id: str, company_name: str, website_url: Optional[str],
                        client_ip: str, recommended_plan: Optional[str],
                        industry: Optional[str], company_size: Optional[str]):
    """Log discover usage to DB. Silently skip on failure."""
    try:
        from app.core.database import async_session
        from app.models.discover_log import DiscoverLog
        async with async_session() as session:
            log = DiscoverLog(
                result_id=result_id,
                company_name=company_name,
                website_url=website_url,
                client_ip=client_ip,
                recommended_plan=recommended_plan,
                industry=industry,
                company_size=company_size,
            )
            session.add(log)
            await session.commit()
    except Exception:
        pass


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
        "recommended_plan": data.get("recommended_plan", "enterprise"),
    }

    # Cache for shareable link
    await _store_result(result_id, response_data)

    # Log to DB for analytics
    await _log_discover(
        result_id=result_id,
        company_name=body.company_name,
        website_url=body.website_url,
        client_ip=client_ip,
        recommended_plan=response_data["recommended_plan"],
        industry=response_data["industry"],
        company_size=response_data["company_size"],
    )

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


@router.post("/{result_id}/feedback")
async def submit_feedback(result_id: str):
    """
    Record a thumbs-up on a discover report.
    PUBLIC endpoint — no auth required.
    """
    try:
        uuid.UUID(result_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid result ID",
        )

    # Update the DB log
    try:
        from app.core.database import async_session
        from app.models.discover_log import DiscoverLog
        from sqlalchemy import update
        async with async_session() as session:
            await session.execute(
                update(DiscoverLog)
                .where(DiscoverLog.result_id == result_id)
                .values(thumbs_up=True)
            )
            await session.commit()
    except Exception:
        pass

    return {"status": "ok", "message": "Thanks for the feedback!"}
