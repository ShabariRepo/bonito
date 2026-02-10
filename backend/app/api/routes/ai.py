"""AI routes — Groq-powered copilot, chat, and command bar."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.ai_service import chat_with_llm, parse_intent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class CopilotRequest(BaseModel):
    message: str
    history: list[dict] = []
    stream: bool = True


class QuickCommandRequest(BaseModel):
    """For Cmd+K command bar — quick intent detection."""
    query: str


def _groq_available() -> bool:
    return bool(settings.groq_api_key)


@router.post("/chat")
async def chat(data: ChatRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Full AI chat — uses Groq copilot when available, falls back to provider LLMs."""
    if _groq_available():
        try:
            from app.services.ai_agent import BonitoCopilot
            copilot = BonitoCopilot(db)
            result = await copilot.chat(data.message, data.history)
            return {
                "intent": "ai_response",
                "confidence": 1.0,
                "message": result["message"],
                "model": result["model"],
                "tokens": result["usage"],
                "provider": "groq",
            }
        except Exception as e:
            logger.warning(f"Groq copilot failed, falling back: {e}")

    # Fallback to cloud provider LLMs
    return await chat_with_llm(data.message, db, data.history)


@router.post("/copilot")
async def copilot(data: CopilotRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Dedicated copilot endpoint with streaming support."""
    if not _groq_available():
        return {"error": "Copilot requires Groq API key", "message": "Configure GROQ_API_KEY to enable the AI copilot."}

    from app.services.ai_agent import BonitoCopilot
    copilot_instance = BonitoCopilot(db)

    if data.stream:
        return StreamingResponse(
            copilot_instance.chat_stream(data.message, data.history),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        result = await copilot_instance.chat(data.message, data.history)
        return result


@router.get("/suggestions")
async def suggestions(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Proactive suggestions based on org state."""
    if not _groq_available():
        return {"suggestions": [
            {"type": "setup", "title": "Enable AI Copilot", "description": "Add a Groq API key to unlock the AI assistant", "priority": "high"},
        ]}

    from app.services.ai_agent import BonitoCopilot
    copilot_instance = BonitoCopilot(db)
    result = await copilot_instance.get_suggestions()
    return {"suggestions": result}


@router.post("/command")
async def command(data: QuickCommandRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Quick command parsing for Cmd+K bar — uses Groq when available."""
    if _groq_available():
        try:
            from app.services.ai_agent import BonitoCopilot
            copilot_instance = BonitoCopilot(db)
            result = await copilot_instance.chat(data.query)
            return {
                "intent": "ai_response",
                "confidence": 1.0,
                "message": result["message"],
                "model": result["model"],
                "provider": "groq",
            }
        except Exception as e:
            logger.warning(f"Groq command failed: {e}")

    return parse_intent(data.query)
