"""
GitHub App API Routes

Webhook handler for GitHub App events (code review on PRs),
OAuth callback for app installation, and setup status endpoint.
"""

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from app.services.github_app_service import (
    get_config,
    handle_installation_event,
    handle_pull_request_event,
    verify_webhook_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["github-app"])


# ─── Schemas ───

class WebhookResponse(BaseModel):
    status: str
    message: str


class SetupStatusResponse(BaseModel):
    configured: bool
    app_id: Optional[str] = None
    install_url: Optional[str] = None
    docs_url: str = "https://docs.getbonito.com/github-app"


# ─── Routes ───

@router.post("/webhook", response_model=WebhookResponse)
async def github_webhook(request: Request):
    """
    Receive GitHub webhook events.

    Verifies the HMAC-SHA256 signature, then dispatches to the appropriate handler.
    The actual review work runs as a background task so we return 200 quickly
    (GitHub requires a response within 10 seconds).
    """
    # 1. Read raw body for signature verification
    body = await request.body()

    # 2. Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_webhook_signature(body, signature):
        logger.warning("Webhook signature verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # 3. Parse event type
    event_type = request.headers.get("X-GitHub-Event", "")
    delivery_id = request.headers.get("X-GitHub-Delivery", "unknown")

    logger.info(f"GitHub webhook received: event={event_type}, delivery={delivery_id}")

    # 4. Parse payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    # 5. Dispatch by event type
    if event_type == "pull_request":
        # Fire-and-forget: run the review in the background
        asyncio.create_task(
            _safe_handle_pr(payload, delivery_id)
        )
        return WebhookResponse(
            status="accepted",
            message="PR review queued",
        )

    elif event_type == "installation":
        # Installation events are fast — handle inline
        try:
            result = await handle_installation_event(payload)
            return WebhookResponse(
                status=result.get("status", "ok"),
                message=f"Installation event processed: {result.get('status', 'ok')}",
            )
        except Exception as e:
            logger.error(f"Installation event handling failed: {e}", exc_info=True)
            return WebhookResponse(status="error", message="Failed to process installation event")

    elif event_type == "ping":
        return WebhookResponse(status="ok", message="pong")

    else:
        logger.debug(f"Ignoring unhandled event type: {event_type}")
        return WebhookResponse(status="ignored", message=f"Event '{event_type}' not handled")


@router.get("/callback")
async def github_callback(
    installation_id: Optional[int] = None,
    setup_action: Optional[str] = None,
    code: Optional[str] = None,
):
    """
    OAuth callback after a user installs the GitHub App.

    GitHub redirects here with installation_id and setup_action.
    In the future this will link the GitHub installation to a Bonito org
    by exchanging the OAuth code for user info.
    """
    if not installation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing installation_id",
        )

    logger.info(
        f"GitHub App callback: installation_id={installation_id}, "
        f"setup_action={setup_action}"
    )

    # TODO: Exchange `code` for user access token, lookup/link Bonito org
    # For now, the installation is auto-tracked via the webhook handler

    return {
        "status": "ok",
        "installation_id": installation_id,
        "setup_action": setup_action,
        "message": "GitHub App installed successfully. Reviews will run automatically on new PRs.",
    }


@router.get("/setup", response_model=SetupStatusResponse)
async def github_setup():
    """
    Returns the current GitHub App configuration status and installation link.
    Used by the frontend to show setup instructions.
    """
    config = get_config()

    if not config.is_configured:
        return SetupStatusResponse(
            configured=False,
            docs_url="https://docs.getbonito.com/github-app",
        )

    install_url = (
        f"https://github.com/apps/bonito-code-review/installations/new"
        if config.app_id
        else None
    )

    return SetupStatusResponse(
        configured=True,
        app_id=config.app_id,
        install_url=install_url,
        docs_url="https://docs.getbonito.com/github-app",
    )


# ─── Helpers ───

async def _safe_handle_pr(payload: dict, delivery_id: str):
    """
    Safely handle a PR event in the background.
    Catches all exceptions to prevent unhandled task errors.
    """
    try:
        result = await handle_pull_request_event(payload)
        logger.info(f"PR review result (delivery={delivery_id}): {result}")
    except Exception as e:
        logger.error(
            f"Background PR review failed (delivery={delivery_id}): {e}",
            exc_info=True,
        )
