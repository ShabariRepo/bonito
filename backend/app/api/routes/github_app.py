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
from app.models.code_snapshot import CodeReviewSnapshot
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

    # Exchange OAuth code for GitHub user info, then link installation to Bonito org
    if code:
        try:
            config = get_config()
            import httpx
            async with httpx.AsyncClient() as client:
                # Step 1: Exchange code for access token
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
                    access_token = token_data.get("access_token")

                    if access_token:
                        # Step 2: Get GitHub user's email
                        emails_resp = await client.get(
                            "https://api.github.com/user/emails",
                            headers={
                                "Authorization": f"token {access_token}",
                                "Accept": "application/vnd.github+json",
                            },
                            timeout=15.0,
                        )
                        github_emails = []
                        if emails_resp.status_code == 200:
                            github_emails = [
                                e["email"] for e in emails_resp.json()
                                if e.get("verified")
                            ]

                        # Step 3: Match GitHub email to a Bonito user and link org
                        if github_emails:
                            async with get_db_session() as db:
                                from app.models.user import User as UserModel
                                for email in github_emails:
                                    stmt = select(UserModel).where(UserModel.email == email)
                                    result = await db.execute(stmt)
                                    bonito_user = result.scalar_one_or_none()
                                    if bonito_user and bonito_user.org_id:
                                        # Link installation to this org
                                        inst_stmt = select(GitHubAppInstallation).where(
                                            GitHubAppInstallation.installation_id == installation_id
                                        )
                                        inst_result = await db.execute(inst_stmt)
                                        inst = inst_result.scalar_one_or_none()
                                        if inst:
                                            inst.org_id = bonito_user.org_id
                                            await db.commit()
                                            logger.info(
                                                f"Linked installation {installation_id} to org "
                                                f"{bonito_user.org_id} via email {email}"
                                            )
                                        break

                        logger.info(f"GitHub OAuth completed for installation {installation_id}")
        except Exception as e:
            logger.warning(f"OAuth token exchange/linking failed: {e}", exc_info=True)

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
    id: str
    repo: str
    pr_number: int
    pr_title: Optional[str] = None
    pr_author: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    snapshots_count: Optional[int] = 0


class CodeReviewStatusResponse(BaseModel):
    connected: bool
    installation: Optional[dict] = None
    persona: str = "default"
    available_personas: List[str] = ["default", "gilfoyle", "dinesh", "richard", "jared", "erlich"]
    usage: int = 0
    limit: int = FREE_TIER_MONTHLY_LIMIT
    reviews: List[ReviewItem] = []


class UpdatePersonaRequest(BaseModel):
    persona: str


class SnapshotItem(BaseModel):
    id: str
    title: str
    severity: str
    category: str
    file_path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    code_block: str
    annotation: str
    sort_order: int
    created_at: str


class SnapshotsResponse(BaseModel):
    review_id: str
    repo: str
    pr_number: int
    pr_title: Optional[str] = None
    pr_author: Optional[str] = None
    snapshots: List[SnapshotItem] = []


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

    # Get recent reviews with snapshot counts
    reviews_stmt = (
        select(GitHubReviewUsage)
        .where(GitHubReviewUsage.installation_id == installation.installation_id)
        .order_by(desc(GitHubReviewUsage.created_at))
        .limit(10)
    )
    reviews_result = await db.execute(reviews_stmt)
    recent_reviews = reviews_result.scalars().all()
    
    # Get snapshot counts for each review
    review_items = []
    for r in recent_reviews:
        snapshots_count_stmt = select(func.count(CodeReviewSnapshot.id)).where(
            CodeReviewSnapshot.review_id == r.id
        )
        snapshots_count_result = await db.execute(snapshots_count_stmt)
        snapshots_count = snapshots_count_result.scalar() or 0
        
        review_items.append(ReviewItem(
            id=str(r.id),
            repo=r.repo_full_name,
            pr_number=r.pr_number,
            pr_title=r.pr_title,
            pr_author=r.pr_author,
            status=r.status,
            created_at=r.created_at.isoformat() if r.created_at else None,
            snapshots_count=snapshots_count,
        ))

    limit = FREE_TIER_MONTHLY_LIMIT if installation.tier == "free" else 999999

    return CodeReviewStatusResponse(
        connected=True,
        persona=getattr(installation, "review_persona", "default") or "default",
        installation={
            "account": installation.github_account_login,
            "account_type": installation.github_account_type,
            "tier": installation.tier,
            "installed_at": installation.installed_at.isoformat() if installation.installed_at else None,
        },
        usage=usage_count,
        limit=limit,
        reviews=review_items,
    )


VALID_PERSONAS = {"default", "gilfoyle", "dinesh", "richard", "jared", "erlich"}


@router.patch("/persona")
async def update_persona(
    body: UpdatePersonaRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the review persona for the user's GitHub App installation."""
    if body.persona not in VALID_PERSONAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid persona. Choose from: {', '.join(sorted(VALID_PERSONAS))}",
        )

    stmt = select(GitHubAppInstallation).where(
        and_(
            GitHubAppInstallation.org_id == user.org_id,
            GitHubAppInstallation.is_active == True,
        )
    )
    result = await db.execute(stmt)
    installation = result.scalar_one_or_none()

    if not installation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No GitHub App installation found. Install the app first.",
        )

    installation.review_persona = body.persona
    await db.commit()

    return {"status": "ok", "persona": body.persona}


# ─── Snapshot Endpoints ───

@router.get("/reviews/{review_id}/snapshots", response_model=SnapshotsResponse)
async def get_review_snapshots(
    review_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get snapshots for a specific review (authenticated).
    Verifies the user's org owns the GitHub installation that created the review.
    """
    try:
        import uuid
        review_uuid = uuid.UUID(review_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid review ID format",
        )

    # Get the review and verify ownership through installation -> org
    review_stmt = (
        select(GitHubReviewUsage)
        .join(GitHubAppInstallation)
        .where(
            and_(
                GitHubReviewUsage.id == review_uuid,
                GitHubAppInstallation.org_id == user.org_id,
            )
        )
    )
    result = await db.execute(review_stmt)
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found or access denied",
        )

    # Get snapshots for this review
    snapshots_stmt = (
        select(CodeReviewSnapshot)
        .where(CodeReviewSnapshot.review_id == review_uuid)
        .order_by(CodeReviewSnapshot.sort_order, CodeReviewSnapshot.created_at)
    )
    snapshots_result = await db.execute(snapshots_stmt)
    snapshots = snapshots_result.scalars().all()

    return SnapshotsResponse(
        review_id=review_id,
        repo=review.repo_full_name,
        pr_number=review.pr_number,
        pr_title=review.pr_title,
        pr_author=review.pr_author,
        snapshots=[
            SnapshotItem(
                id=str(s.id),
                title=s.title,
                severity=s.severity,
                category=s.category,
                file_path=s.file_path,
                start_line=s.start_line,
                end_line=s.end_line,
                code_block=s.code_block,
                annotation=s.annotation,
                sort_order=s.sort_order,
                created_at=s.created_at.isoformat() if s.created_at else "",
            )
            for s in snapshots
        ],
    )


@router.get("/snapshots/{review_id}", response_model=SnapshotsResponse)
async def get_public_snapshots(
    review_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get snapshots for a specific review (public endpoint, no auth).
    Uses security through obscurity - the UUID is unguessable.
    This is the endpoint used by the public snapshot viewer page.
    """
    try:
        import uuid
        review_uuid = uuid.UUID(review_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid review ID format",
        )

    # Get the review
    review_stmt = select(GitHubReviewUsage).where(GitHubReviewUsage.id == review_uuid)
    result = await db.execute(review_stmt)
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    # Get snapshots for this review
    snapshots_stmt = (
        select(CodeReviewSnapshot)
        .where(CodeReviewSnapshot.review_id == review_uuid)
        .order_by(CodeReviewSnapshot.sort_order, CodeReviewSnapshot.created_at)
    )
    snapshots_result = await db.execute(snapshots_stmt)
    snapshots = snapshots_result.scalars().all()

    return SnapshotsResponse(
        review_id=review_id,
        repo=review.repo_full_name,
        pr_number=review.pr_number,
        pr_title=review.pr_title,
        pr_author=review.pr_author,
        snapshots=[
            SnapshotItem(
                id=str(s.id),
                title=s.title,
                severity=s.severity,
                category=s.category,
                file_path=s.file_path,
                start_line=s.start_line,
                end_line=s.end_line,
                code_block=s.code_block,
                annotation=s.annotation,
                sort_order=s.sort_order,
                created_at=s.created_at.isoformat() if s.created_at else "",
            )
            for s in snapshots
        ],
    )


# ─── Debug (temporary) ───

@router.get("/debug/installations")
async def debug_installations(db: AsyncSession = Depends(get_db)):
    """Temporary debug: list all installations and their org links. Remove after fixing."""
    stmt = select(GitHubAppInstallation)
    result = await db.execute(stmt)
    installations = result.scalars().all()

    # Also get all users with their org_ids for cross-reference
    from app.models.user import User as UserModel
    users_stmt = select(UserModel)
    users_result = await db.execute(users_stmt)
    users = users_result.scalars().all()

    return {
        "installations": [
            {
                "installation_id": inst.installation_id,
                "github_account": inst.github_account_login,
                "org_id": str(inst.org_id) if inst.org_id else None,
                "tier": inst.tier,
                "is_active": inst.is_active,
            }
            for inst in installations
        ],
        "users": [
            {
                "email": u.email,
                "org_id": str(u.org_id) if u.org_id else None,
            }
            for u in users
        ],
    }


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
