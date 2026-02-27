"""
Widget API Routes

Public-facing endpoints for the embeddable chat widget.
No auth required — these are accessed from customer websites.
"""

import time
import uuid
from collections import defaultdict
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.models.agent import Agent
from fastapi import Depends

router = APIRouter(prefix="/widget", tags=["widget"])


# ─── Simple in-memory rate limiter (fallback if Redis unavailable) ───

_rate_limit_store: Dict[str, list] = defaultdict(list)
RATE_LIMIT_RPM = 20
RATE_LIMIT_WINDOW = 60  # seconds


def _check_rate_limit(client_ip: str) -> bool:
    """Check if client IP is within rate limit. Returns True if allowed."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    # Clean old entries
    _rate_limit_store[client_ip] = [
        ts for ts in _rate_limit_store[client_ip] if ts > window_start
    ]

    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_RPM:
        return False

    _rate_limit_store[client_ip].append(now)
    return True


# ─── Schemas ───

class WidgetConfigResponse(BaseModel):
    agent_id: str
    agent_name: str
    welcome_message: str
    suggested_questions: list
    theme: str
    accent_color: str


class WidgetChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[str] = None


class WidgetChatResponse(BaseModel):
    content: Optional[str]
    session_id: str


# ─── Routes ───

@router.get("/{agent_id}/config", response_model=WidgetConfigResponse)
async def get_widget_config(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get widget configuration for an agent.
    PUBLIC endpoint — no auth required.
    """
    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agent ID",
        )

    stmt = select(Agent).where(
        and_(
            Agent.id == agent_uuid,
            Agent.status == "active",
            Agent.widget_enabled == True,
        )
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found or not enabled for this agent",
        )

    widget_config = agent.widget_config or {}

    return WidgetConfigResponse(
        agent_id=str(agent.id),
        agent_name=agent.name,
        welcome_message=widget_config.get("welcome_message", "Hi! How can I help you?"),
        suggested_questions=widget_config.get("suggested_questions", []),
        theme=widget_config.get("theme", "light"),
        accent_color=widget_config.get("accent_color", "#6366f1"),
    )


@router.post("/{agent_id}/chat", response_model=WidgetChatResponse)
async def widget_chat(
    agent_id: str,
    body: WidgetChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Chat with an agent via widget.
    PUBLIC but rate-limited (20 req/min per IP).
    """
    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a moment before sending another message.",
        )

    try:
        agent_uuid = uuid.UUID(agent_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agent ID",
        )

    # Validate agent exists and has widget enabled
    stmt = select(Agent).where(
        and_(
            Agent.id == agent_uuid,
            Agent.status == "active",
            Agent.widget_enabled == True,
        )
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found or not enabled for this agent",
        )

    # Execute via agent engine
    try:
        from app.services.agent_engine import AgentEngine
        from app.core.redis import get_redis

        engine = AgentEngine()
        session_uuid = uuid.UUID(body.session_id) if body.session_id else None

        run_result = await engine.execute(
            agent=agent,
            message=body.message,
            session_id=session_uuid,
            db=db,
            redis=await get_redis(),
            user_id=None,  # Widget users are anonymous
        )

        # Find the session ID
        if session_uuid:
            response_session_id = str(session_uuid)
        else:
            from sqlalchemy import desc
            from app.models.agent_session import AgentSession

            stmt = (
                select(AgentSession.id)
                .where(AgentSession.agent_id == agent_uuid)
                .order_by(desc(AgentSession.last_message_at))
                .limit(1)
            )
            db_result = await db.execute(stmt)
            new_session_id = db_result.scalar_one_or_none()
            response_session_id = str(new_session_id) if new_session_id else str(uuid.uuid4())

        return WidgetChatResponse(
            content=run_result.content,
            session_id=response_session_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred. Please try again.",
        )
