"""
GitHub App API Routes

Webhook handler for GitHub App events (code review on PRs),
OAuth callback for app installation, and setup status endpoint.
"""

import asyncio
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.models.github_app import GitHubAppInstallation, GitHubReviewUsage
from app.models.user import User
from app.services.github_app_service import (
    get_config,
    handle_installation_event,
    handle_pull_request_event,
    verify_webhook_signature,
    FREE_TIER_MONTHLY_LIMIT,
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
    Redirects the user back to the Bonito dashboard Code Review page.
    """
    from starlette.responses import RedirectResponse
    from app.core.database import get_db_session

    if not installation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing installation_id",
        )

    logger.info(
        f"GitHub App callback: installation_id={installation_id}, "
        f"setup_action={setup_action}"
    )

    # If we have an OAuth code, exchange it for user info and link to org
    if code:
        try:
            config = get_config()
            import httpx
            async with httpx.AsyncClient() as client:
                # Exchange code for access token
                token_resp = await client.post(
                    "https://github.com/login/oauth/access_token",
                    json={
                        "client_id": config.client_id,
                        "client_secret": config.client_secret,
                        "code": code,
                    },
                    headers={"Accept": "application/json"},
                    timeout=15.0,
                )
                if token_resp.status_code == 200:
                    token_data = token_resp.json()
                    logger.info(f"GitHub OAuth token exchanged for installation {installation_id}")
        except Exception as e:
            logger.warning(f"OAuth token exchange failed: {e}")

    # Redirect to dashboard code review page
    return RedirectResponse(
        url=f"https://getbonito.com/code-review?installed=true&installation_id={installation_id}",
        status_code=302,
    )


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


# ─── Authenticated Endpoints ───

class ReviewItem(BaseModel):
    repo: str
    pr_number: int
    pr_title: Optional[str] = None
    pr_author: Optional[str] = None
    status: str
    created_at: Optional[str] = None


class CodeReviewStatusResponse(BaseModel):
    connected: bool
    installation: Optional[dict] = None
    usage: int = 0
    limit: int = FREE_TIER_MONTHLY_LIMIT
    reviews: List[ReviewItem] = []


@router.get("/status", response_model=CodeReviewStatusResponse)
async def github_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the current user's GitHub App connection status, usage, and recent reviews.
    Requires authentication.
    """
    from datetime import datetime, timezone

    # Find installation linked to user's org
    stmt = select(GitHubAppInstallation).where(
        and_(
            GitHubAppInstallation.org_id == user.org_id,
            GitHubAppInstallation.is_active == True,
        )
    )
    result = await db.execute(stmt)
    installation = result.scalar_one_or_none()

    if not installation:
        return CodeReviewStatusResponse(connected=False)

    # Get monthly usage
    billing_period = datetime.now(timezone.utc).strftime("%Y-%m")
    usage_stmt = select(func.count(GitHubReviewUsage.id)).where(
        and_(
            GitHubReviewUsage.installation_id == installation.installation_id,
            GitHubReviewUsage.billing_period == billing_period,
            GitHubReviewUsage.status.in_(["completed", "in_progress"]),
        )
    )
    usage_result = await db.execute(usage_stmt)
    usage_count = usage_result.scalar() or 0

    # Get recent reviews
    reviews_stmt = (
        select(GitHubReviewUsage)
        .where(GitHubReviewUsage.installation_id == installation.installation_id)
        .order_by(desc(GitHubReviewUsage.created_at))
        .limit(10)
    )
    reviews_result = await db.execute(reviews_stmt)
    recent_reviews = reviews_result.scalars().all()

    limit = FREE_TIER_MONTHLY_LIMIT if installation.tier == "free" else 999999

    return CodeReviewStatusResponse(
        connected=True,
        installation={
            "account": installation.github_account_login,
            "account_type": installation.github_account_type,
            "tier": installation.tier,
            "installed_at": installation.installed_at.isoformat() if installation.installed_at else None,
        },
        usage=usage_count,
        limit=limit,
        reviews=[
            ReviewItem(
                repo=r.repo_full_name,
                pr_number=r.pr_number,
                pr_title=r.pr_title,
                pr_author=r.pr_author,
                status=r.status,
                created_at=r.created_at.isoformat() if r.created_at else None,
            )
            for r in recent_reviews
        ],
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
