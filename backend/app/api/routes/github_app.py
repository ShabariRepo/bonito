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
    
    # Extract review data first (before any queries that might invalidate the session)
    review_data = [
        {
            "id": str(r.id),
            "repo": r.repo_full_name,
            "pr_number": r.pr_number,
            "pr_title": r.pr_title,
            "pr_author": r.pr_author,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "review_uuid": r.id,
        }
        for r in recent_reviews
    ]

    # Get snapshot counts (graceful if table doesn't exist yet)
    snapshot_counts = {}
    try:
        for rd in review_data:
            snapshots_count_stmt = select(func.count(CodeReviewSnapshot.id)).where(
                CodeReviewSnapshot.review_id == rd["review_uuid"]
            )
            snapshots_count_result = await db.execute(snapshots_count_stmt)
            snapshot_counts[rd["id"]] = snapshots_count_result.scalar() or 0
    except Exception:
        # Table may not exist yet (migration not run) -- skip all snapshot counts
        snapshot_counts = {}

    review_items = [
        ReviewItem(
            id=rd["id"],
            repo=rd["repo"],
            pr_number=rd["pr_number"],
            pr_title=rd["pr_title"],
            pr_author=rd["pr_author"],
            status=rd["status"],
            created_at=rd["created_at"],
            snapshots_count=snapshot_counts.get(rd["id"], 0),
        )
        for rd in review_data
    ]

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


# ─── Test/Debug Endpoints ───

class TestSnapshotRequest(BaseModel):
    persona: str = "default"
    repo: str = "test-org/test-repo"
    pr_number: int = 42
    pr_title: str = "Test PR for snapshot debugging"


class TestSnapshotResponse(BaseModel):
    status: str
    review_id: str
    message: str


@router.post("/reviews/test-snapshot", response_model=TestSnapshotResponse)
async def create_test_snapshot(
    body: TestSnapshotRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a mock review with sample snapshots for testing the snapshot pipeline.
    This allows testing without needing Bedrock access or actual PR webhooks.
    """
    import uuid
    from datetime import datetime, timezone
    
    # Create or get a mock installation for this org
    stmt = select(GitHubAppInstallation).where(
        GitHubAppInstallation.org_id == user.org_id
    )
    result = await db.execute(stmt)
    installation = result.scalar_one_or_none()
    
    if not installation:
        # Create a mock installation
        installation = GitHubAppInstallation(
            installation_id=999999,  # Mock installation ID
            github_account_login=user.email.split("@")[0] if user.email else "test-user",
            github_account_id=999999,
            github_account_type="User",
            org_id=user.org_id,
            tier="free",
            review_persona=body.persona,
            is_active=True,
        )
        db.add(installation)
        await db.flush()
    
    # Create a mock review record
    billing_period = datetime.now(timezone.utc).strftime("%Y-%m")
    review = GitHubReviewUsage(
        installation_id=installation.installation_id,
        installation_ref=installation.id,
        repo_full_name=body.repo,
        pr_number=body.pr_number,
        pr_title=body.pr_title,
        pr_author=user.email or "test@example.com",
        commit_sha="abc123def456",
        billing_period=billing_period,
        status="completed",
        completed_at=datetime.now(timezone.utc),
        review_summary="Mock review for testing snapshots feature",
    )
    db.add(review)
    await db.flush()
    
    # Create sample snapshots
    mock_snapshots = [
        {
            "title": "SQL Injection Vulnerability in User Query",
            "severity": "critical",
            "category": "security",
            "file_path": "src/auth/login.py",
            "start_line": 45,
            "end_line": 52,
            "code_block": 'def authenticate_user(username, password):\n    query = f"SELECT * FROM users WHERE username = \'{username}\'"\n    result = db.execute(query)\n    return result.fetchone()',
            "annotation": "This code is vulnerable to SQL injection. The username parameter is directly interpolated into the SQL query without sanitization. An attacker could input username: admin' OR '1'='1 to bypass authentication.",
        },
        {
            "title": "Inefficient N+1 Query Pattern",
            "severity": "warning",
            "category": "performance",
            "file_path": "src/api/users.py",
            "start_line": 120,
            "end_line": 135,
            "code_block": "def get_users_with_orders():\n    users = User.query.all()\n    for user in users:\n        # This triggers a new query for each user!\n        orders = Order.query.filter_by(user_id=user.id).all()\n        user.orders_count = len(orders)\n    return users",
            "annotation": "This is a classic N+1 query problem. For each of N users, an additional query is executed to fetch orders. With 100 users, this results in 101 database queries. Consider using joinedload() or a single aggregated query.",
        },
        {
            "title": "Hardcoded API Key",
            "severity": "critical",
            "category": "security",
            "file_path": "src/config/settings.py",
            "start_line": 15,
            "end_line": 18,
            "code_block": '# Production API key\nSTRIPE_API_KEY = "REDACTED"\n\n# Database config\nDB_HOST = "localhost"',
            "annotation": "Hardcoded API keys in source code are a security risk. This Stripe live key should be moved to environment variables and the current key should be rotated immediately.",
        },
        {
            "title": "Missing Error Handling in Async Function",
            "severity": "suggestion",
            "category": "logic",
            "file_path": "src/services/payment.py",
            "start_line": 88,
            "end_line": 98,
            "code_block": "async def process_payment(order_id):\n    order = await get_order(order_id)\n    result = await stripe.charge(order.total)\n    order.payment_id = result.id\n    await order.save()\n    return result",
            "annotation": "This async function lacks error handling. If the Stripe charge fails or the order doesn't exist, the function will raise an unhandled exception. Consider wrapping external API calls in try-except blocks and handling specific error cases.",
        },
        {
            "title": "Large Component Without Memoization",
            "severity": "suggestion",
            "category": "performance",
            "file_path": "frontend/src/components/DataTable.tsx",
            "start_line": 24,
            "end_line": 78,
            "code_block": "function DataTable({ data, columns }) {\n  // Expensive filtering on every render\n  const filteredData = data\n    .filter(row => row.isActive)\n    .map(row => ({\n      ...row,\n      computed: expensiveCalculation(row.value)\n    }));\n\n  return (\n    <table>\n      {filteredData.map(row => <Row key={row.id} {...row} />)}\n    </table>\n  );\n}",
            "annotation": "The expensive filtering and computation runs on every render. Consider using useMemo to cache the filtered results and prevent unnecessary recalculation when data hasn't changed.",
        },
        {
            "title": "Race Condition in State Update",
            "severity": "warning",
            "category": "logic",
            "file_path": "src/hooks/useCounter.ts",
            "start_line": 8,
            "end_line": 14,
            "code_block": "const increment = () => {\n  setCount(count + 1);\n};\n\nconst handleDoubleClick = () => {\n  increment();\n  increment();\n};",
            "annotation": "React state updates are batched and asynchronous. When increment() is called twice, both calls use the same stale value of count. Use the functional update form: setCount(c => c + 1) to ensure atomic updates.",
        },
        {
            "title": "Good Practice: Input Validation",
            "severity": "info",
            "category": "architecture",
            "file_path": "src/validators/user.py",
            "start_line": 10,
            "end_line": 28,
            "code_block": "class UserValidator:\n    @staticmethod\n    def validate_email(email: str) -> bool:\n        \"\"\"Validate email format and domain.\"\"\"\n        if not email or '@' not in email:\n            return False\n        _, domain = email.split('@')\n        return domain in ALLOWED_DOMAINS",
            "annotation": "Good example of defensive programming! The validator checks for empty strings, proper format, and restricts to allowed domains. Consider also adding length limits and normalization (lowercase, strip whitespace).",
        },
    ]
    
    # Filter to 3-5 snapshots based on requested persona
    if body.persona == "gilfoyle":
        # Gilfoyle focuses on security issues and critical bugs
        filtered = [s for s in mock_snapshots if s["severity"] in ["critical", "warning"]]
    elif body.persona == "dinesh":
        # Dinesh focuses on everything to show off
        filtered = mock_snapshots[:5]
    else:
        filtered = mock_snapshots[:4]
    
    # Save snapshots to database
    severity_order = {"critical": 0, "warning": 1, "suggestion": 2, "info": 3}
    
    for i, snapshot_data in enumerate(filtered):
        base_order = severity_order.get(snapshot_data["severity"], 3)
        sort_order = base_order * 100 + i
        
        snapshot = CodeReviewSnapshot(
            review_id=review.id,
            title=snapshot_data["title"],
            severity=snapshot_data["severity"],
            category=snapshot_data["category"],
            file_path=snapshot_data["file_path"],
            start_line=snapshot_data["start_line"],
            end_line=snapshot_data["end_line"],
            code_block=snapshot_data["code_block"],
            annotation=snapshot_data["annotation"],
            sort_order=sort_order,
        )
        db.add(snapshot)
    
    await db.commit()
    
    logger.info(f"Created test snapshot review {review.id} with {len(filtered)} snapshots")
    
    return TestSnapshotResponse(
        status="success",
        review_id=str(review.id),
        message=f"Created mock review with {len(filtered)} snapshots. View at /snapshots/{review.id}",
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
