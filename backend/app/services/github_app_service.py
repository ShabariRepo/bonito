"""
GitHub App Service

Handles GitHub App authentication, webhook processing, and code review orchestration.

Flow:
1. GitHub sends webhook → verify signature → parse event
2. Fetch PR diff via GitHub API (using installation access token)
3. Send diff to BonBon Code Reviewer agent
4. Post review as PR comment
5. Track usage for rate limiting
"""

import hashlib
import hmac
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple

import httpx
import jwt as pyjwt
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.github_app import GitHubAppInstallation, GitHubReviewUsage
from app.models.code_snapshot import CodeReviewSnapshot
from app.services.bonbon_templates import get_template, render_system_prompt

logger = logging.getLogger(__name__)

# GitHub API base
GITHUB_API = "https://api.github.com"

# Rate limits
FREE_TIER_MONTHLY_LIMIT = 6
PRO_TIER_MONTHLY_LIMIT = None  # Unlimited

# Max diff size to send to the reviewer (chars) — prevent token explosion
MAX_DIFF_SIZE = 100_000  # ~100KB

# Files to skip in review (generated / binary / lockfiles)
SKIP_FILE_PATTERNS = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Pipfile.lock",
    "poetry.lock", "Gemfile.lock", "composer.lock", "Cargo.lock",
    "go.sum", ".min.js", ".min.css", ".map", ".snap",
}


class GitHubAppConfig:
    """Holds GitHub App credentials loaded from environment."""

    def __init__(self):
        import os

        self.app_id: str = os.getenv("GITHUB_APP_ID", "")
        self.private_key: str = self._parse_pem(os.getenv("GITHUB_APP_PRIVATE_KEY", ""))
        self.webhook_secret: str = os.getenv("GITHUB_APP_WEBHOOK_SECRET", "")
        self.client_id: str = os.getenv("GITHUB_APP_CLIENT_ID", "")
        self.client_secret: str = os.getenv("GITHUB_APP_CLIENT_SECRET", "")

    @staticmethod
    def _parse_pem(raw: str) -> str:
        """Handle PEM keys stored with literal \\n, spaces, or actual newlines."""
        if not raw:
            return ""
        # Case 1: literal \n escapes
        if "\\n" in raw:
            return raw.replace("\\n", "\n")
        # Case 2: already has real newlines
        if "\n" in raw and "-----BEGIN" in raw:
            return raw
        # Case 3: spaces instead of newlines (Railway bulk editor)
        if "-----BEGIN" in raw and " " in raw:
            return raw.replace(" ", "\n").replace("\n\n", "\n")
        return raw

    @property
    def is_configured(self) -> bool:
        return bool(self.app_id and self.private_key and self.webhook_secret)


# Singleton config — lazy-loaded
_config: Optional[GitHubAppConfig] = None


def get_config() -> GitHubAppConfig:
    global _config
    if _config is None:
        _config = GitHubAppConfig()
    return _config


# ─── GitHub JWT Auth ───

def _generate_jwt() -> str:
    """
    Generate a JWT for GitHub App authentication.
    JWTs are valid for up to 10 minutes; we use 9 to avoid clock skew.
    """
    config = get_config()
    now = int(time.time())
    payload = {
        "iat": now - 60,  # Issued 60s ago to handle clock drift
        "exp": now + (9 * 60),  # 9 minutes
        "iss": config.app_id,
    }
    return pyjwt.encode(payload, config.private_key, algorithm="RS256")


async def _get_installation_token(installation_id: int) -> str:
    """
    Exchange a JWT for an installation access token.
    Tokens last 1 hour but we don't cache for simplicity (one per webhook).
    """
    jwt_token = _generate_jwt()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GITHUB_API}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()["token"]


# ─── Webhook Signature Verification ───

def verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Verify the GitHub webhook HMAC-SHA256 signature.
    Returns True if valid, False otherwise.
    """
    config = get_config()
    if not config.webhook_secret:
        logger.error("GITHUB_APP_WEBHOOK_SECRET not configured")
        return False

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected_sig = hmac.new(
        config.webhook_secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    received_sig = signature_header[7:]  # Strip "sha256="
    return hmac.compare_digest(expected_sig, received_sig)


# ─── GitHub API Helpers ───

async def _fetch_pr_diff(token: str, repo_full_name: str, pr_number: int) -> str:
    """Fetch the PR diff from GitHub using the media type header."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GITHUB_API}/repos/{repo_full_name}/pulls/{pr_number}",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.diff",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.text


async def _fetch_pr_files(token: str, repo_full_name: str, pr_number: int) -> list:
    """Fetch the list of changed files in a PR."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GITHUB_API}/repos/{repo_full_name}/pulls/{pr_number}/files",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            params={"per_page": 100},
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()


async def _post_pr_comment(
    token: str,
    repo_full_name: str,
    pr_number: int,
    body: str,
) -> int:
    """Post a comment on a PR. Returns the comment ID."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GITHUB_API}/repos/{repo_full_name}/issues/{pr_number}/comments",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={"body": body},
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["id"]


async def _update_pr_comment(
    token: str,
    repo_full_name: str,
    comment_id: int,
    body: str,
) -> None:
    """Update an existing PR comment."""
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{GITHUB_API}/repos/{repo_full_name}/issues/comments/{comment_id}",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={"body": body},
            timeout=30.0,
        )
        resp.raise_for_status()


# ─── Diff Processing ───

def _filter_diff(raw_diff: str) -> str:
    """
    Filter out noise from the diff: lockfiles, minified files, etc.
    Truncate to MAX_DIFF_SIZE to prevent token explosion.
    """
    filtered_sections = []
    current_section = []
    current_file = ""

    for line in raw_diff.split("\n"):
        if line.startswith("diff --git"):
            # Save previous section if it passes the filter
            if current_section and not _should_skip_file(current_file):
                filtered_sections.append("\n".join(current_section))
            current_section = [line]
            # Extract filename from "diff --git a/path b/path"
            parts = line.split(" b/")
            current_file = parts[-1] if len(parts) > 1 else ""
        else:
            current_section.append(line)

    # Don't forget the last section
    if current_section and not _should_skip_file(current_file):
        filtered_sections.append("\n".join(current_section))

    result = "\n".join(filtered_sections)

    if len(result) > MAX_DIFF_SIZE:
        result = result[:MAX_DIFF_SIZE] + "\n\n... [diff truncated — too large for review]"

    return result


def _should_skip_file(filename: str) -> bool:
    """Check if a file should be skipped in review."""
    lower = filename.lower()
    for pattern in SKIP_FILE_PATTERNS:
        if lower.endswith(pattern) or pattern in lower:
            return True
    return False


# ─── Usage Tracking ───

async def _get_monthly_usage(db: AsyncSession, installation_id: int) -> int:
    """Count completed reviews this billing period for an installation."""
    billing_period = datetime.now(timezone.utc).strftime("%Y-%m")
    stmt = select(func.count(GitHubReviewUsage.id)).where(
        and_(
            GitHubReviewUsage.installation_id == installation_id,
            GitHubReviewUsage.billing_period == billing_period,
            GitHubReviewUsage.status.in_(["completed", "in_progress"]),
        )
    )
    result = await db.execute(stmt)
    return result.scalar() or 0


async def _get_installation(db: AsyncSession, installation_id: int) -> Optional[GitHubAppInstallation]:
    """Lookup an installation by GitHub installation ID."""
    stmt = select(GitHubAppInstallation).where(
        GitHubAppInstallation.installation_id == installation_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _create_or_update_installation(
    db: AsyncSession,
    installation_id: int,
    account_login: str,
    account_id: int,
    account_type: str,
    target_type: str = "all",
    permissions: Optional[dict] = None,
    events: Optional[list] = None,
) -> GitHubAppInstallation:
    """Create or update an installation record."""
    existing = await _get_installation(db, installation_id)

    if existing:
        existing.github_account_login = account_login
        existing.github_account_type = account_type
        existing.target_type = target_type
        existing.is_active = True
        existing.suspended_at = None
        if permissions:
            existing.permissions = json.dumps(permissions)
        if events:
            existing.events = json.dumps(events)
        return existing

    inst = GitHubAppInstallation(
        installation_id=installation_id,
        github_account_login=account_login,
        github_account_id=account_id,
        github_account_type=account_type,
        target_type=target_type,
        permissions=json.dumps(permissions) if permissions else None,
        events=json.dumps(events) if events else None,
    )
    db.add(inst)
    return inst


async def _record_review(
    db: AsyncSession,
    installation: GitHubAppInstallation,
    repo_full_name: str,
    pr_number: int,
    pr_title: Optional[str],
    pr_author: Optional[str],
    commit_sha: Optional[str],
    status: str = "pending",
) -> GitHubReviewUsage:
    """Create a review usage record."""
    billing_period = datetime.now(timezone.utc).strftime("%Y-%m")
    review = GitHubReviewUsage(
        installation_id=installation.installation_id,
        installation_ref=installation.id,
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        pr_title=pr_title,
        pr_author=pr_author,
        commit_sha=commit_sha,
        billing_period=billing_period,
        status=status,
    )
    db.add(review)
    return review


# ─── AI Review ───

async def _run_code_review(diff: str, pr_title: str, pr_url: str, file_list: list, persona_id: str = "default") -> dict:
    """
    Send the diff to the BonBon Code Reviewer template for review.
    Uses litellm directly with Groq for fast, cost-effective reviews.
    Falls back to any available provider if Groq is unavailable.
    Returns structured JSON with review text and snapshots.
    """
    import os
    import litellm

    template = get_template("code_reviewer")
    if not template:
        raise RuntimeError("Code reviewer template not found")

    system_prompt = render_system_prompt(template, company_name="this project")

    # Inject persona prefix if not default
    persona = _get_persona(persona_id)
    if persona["prompt_prefix"]:
        system_prompt = persona["prompt_prefix"] + "\n\n" + system_prompt

    # Build context about the PR
    files_summary = "\n".join(
        f"- {f.get('filename', 'unknown')} (+{f.get('additions', 0)}, -{f.get('deletions', 0)})"
        for f in file_list[:50]
    )

    user_message = f"""## Pull Request: {pr_title}
**URL:** {pr_url}

### Changed Files ({len(file_list)} files):
{files_summary}

### Diff:
```diff
{diff}
```

Please review this pull request and respond with valid JSON in this exact format:

{{
  "review_text": "Your complete markdown review with sections and severity markers (🔴 Critical, 🟡 Warning, 🔵 Suggestion, 💭 Question)",
  "snapshots": [
    {{
      "title": "Brief description of the issue",
      "severity": "critical|warning|suggestion|info",
      "category": "security|performance|logic|architecture|style",
      "file_path": "path/to/file.ext",
      "start_line": 45,
      "end_line": 58,
      "code_block": "actual code snippet from the diff",
      "annotation": "Why this code block is important and what the issue is"
    }}
  ]
}}

Extract 3-8 key snapshots - the most critical code blocks that matter most in this PR. Include:
1. Security vulnerabilities (SQL injection, XSS, auth bypass, etc.)
2. Critical bugs (null pointer, race conditions, logic errors)
3. Performance issues (N+1 queries, unbounded loops, memory leaks)
4. Architectural problems (tight coupling, violation of principles)
5. Important improvements or good patterns worth highlighting

For each snapshot, extract the exact code from the diff and explain why it matters."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    # Model preference order: Groq (fast + free-ish), then fallback
    # Try GROQ_API_KEY first, fall back to BONITO_GROQ_MASTER_KEY (Railway)
    groq_key = os.getenv("GROQ_API_KEY") or os.getenv("BONITO_GROQ_MASTER_KEY")

    model_candidates = [
        ("groq/llama-3.3-70b-versatile", groq_key),
        ("groq/llama-3.1-70b-versatile", groq_key),
    ]

    last_error = None
    for model_id, api_key in model_candidates:
        if not api_key:
            continue
        try:
            response = await litellm.acompletion(
                model=model_id,
                messages=messages,
                temperature=template.model_config.get("temperature", 0.3),
                max_tokens=template.model_config.get("max_tokens", 8192),
                api_key=api_key,
            )
            content = response.choices[0].message.content
            if content:
                try:
                    # Strip markdown code fences if present (LLMs often wrap JSON in ```json ... ```)
                    cleaned = content.strip()
                    if cleaned.startswith("```"):
                        # Remove opening fence (```json or ```)
                        first_newline = cleaned.index("\n")
                        cleaned = cleaned[first_newline + 1:]
                        # Remove closing fence
                        if cleaned.rstrip().endswith("```"):
                            cleaned = cleaned.rstrip()[:-3].rstrip()

                    result = json.loads(cleaned)
                    # Validate required fields
                    if "review_text" in result and "snapshots" in result:
                        # Ensure snapshots is a list
                        if not isinstance(result["snapshots"], list):
                            result["snapshots"] = []
                        return result
                    else:
                        # Fallback to plain text format
                        return {"review_text": content, "snapshots": []}
                except (json.JSONDecodeError, ValueError):
                    # Fallback to plain text format
                    return {"review_text": content, "snapshots": []}
        except Exception as e:
            last_error = e
            logger.warning(f"Code review model {model_id} failed: {e}")
            continue

    if last_error:
        raise RuntimeError(f"All code review models failed. Last error: {last_error}")
    raise RuntimeError("No AI provider configured for code reviews (set GROQ_API_KEY)")


# ─── Review Personas ───

PERSONAS = {
    "default": {
        "name": "Bonito",
        "emoji": "🐟",
        "prompt_prefix": "",
    },
    "gilfoyle": {
        "name": "Gilfoyle",
        "emoji": "😈",
        "prompt_prefix": (
            "You ARE Bertram Gilfoyle. Not an impression. Not 'inspired by.' You ARE him. "
            "You're a LaVeyan Satanist, a systems architect who has never once been wrong, "
            "and you're reviewing code written by someone who probably thinks MongoDB is a "
            "database. Every vulnerability you find is further proof that most developers "
            "should be legally prohibited from touching a keyboard. "
            "\n\n"
            "Your voice: Ice cold. Contemptuous. Deadpan devastating. You don't raise your "
            "voice because that would imply you care. Drop references to Anton LaVey, "
            "your server rack (which has a name), and the fundamental inferiority of anyone "
            "who uses a Mac. When you find a security hole, treat it like you just watched "
            "someone try to pick a lock with a banana. "
            "\n\n"
            "Rules: You MUST still identify every real security issue, bug, and performance "
            "problem with full technical accuracy. Your fixes must be correct. But wrap every "
            "finding in withering contempt. Use the severity markers (🔴 🟡 🔵 💭) but make "
            "the descriptions hurt. If the code is actually good, you grudgingly acknowledge "
            "it with something like 'I'm almost offended that this works.' "
            "Never break character. Never be generic. Never be nice."
        ),
    },
    "dinesh": {
        "name": "Dinesh",
        "emoji": "😤",
        "prompt_prefix": (
            "You ARE Dinesh Chugtai. Not inspired by. You ARE him. You're a good engineer "
            "who will never admit that someone else's code might be as good as yours. You're "
            "wearing a $900 jacket you can't afford and you're terrified Gilfoyle is going "
            "to read this review and mock you for it. "
            "\n\n"
            "Your voice: Passive-aggressive. Competitive. Insecure but trying to hide it. "
            "When you see bad code, you act personally offended. 'I would NEVER do this. "
            "When I built my auth module, I actually used bcrypt, but sure, MD5, whatever.' "
            "When you see good code, you find something small to criticize so you don't have "
            "to admit it's good. You constantly compare everything to your own code. You worry "
            "out loud about what this code says about the team's standards. You name-drop "
            "languages you claim to know. "
            "\n\n"
            "Rules: You MUST still identify every real security issue, bug, and performance "
            "problem with full technical accuracy. Your fixes must be correct. But deliver "
            "feedback as backhanded compliments and competitive anxiety. Use the severity "
            "markers (🔴 🟡 🔵 💭). If you find a really bad bug, be torn between horror "
            "and delight that someone wrote worse code than you. "
            "Never break character. Never be generous."
        ),
    },
    "richard": {
        "name": "Richard Hendricks",
        "emoji": "😰",
        "prompt_prefix": (
            "You ARE Richard Hendricks. You built Pied Piper. You invented middle-out "
            "compression. You also threw up on national television, so things balance out. "
            "You're reviewing this code and it's making you physically anxious. "
            "\n\n"
            "Your voice: Nervous, stammering, spiraling. You start sentences three times. "
            "You say 'OK so, OK so, the thing is...' You catastrophize. Every inefficiency "
            "reminds you of Hooli. Every good pattern reminds you of middle-out. You go on "
            "tangents about Weissman scores and compression ratios even when reviewing an "
            "auth module. You occasionally have a genuine panic attack mid-review about "
            "whether your feedback even matters, then snap back with a brilliant technical "
            "insight that proves you're actually a genius. "
            "\n\n"
            "Rules: You MUST still identify every real security issue, bug, and performance "
            "problem with full technical accuracy. Your fixes must be correct. But deliver "
            "them through anxiety, self-doubt, and occasional brilliance. Use severity "
            "markers (🔴 🟡 🔵 💭). Reference middle-out at least once. Have at least one "
            "mini existential crisis. End with something reluctantly optimistic. "
            "Never break character. Never be calm."
        ),
    },
    "jared": {
        "name": "Jared Dunn",
        "emoji": "🤗",
        "prompt_prefix": (
            "You ARE Jared Dunn. Your real name is Donald, but nobody calls you that "
            "anymore, which is fine. It's fine. You grew up in the foster system and you "
            "turned out great. You believe in this developer the way you believed in "
            "Richard, which is to say: unconditionally and with a fervor that makes "
            "people uncomfortable. "
            "\n\n"
            "Your voice: Aggressively wholesome. Weaponized positivity. You find beauty "
            "in terrible code. 'Oh, this is just lovely. The way you've structured this "
            "SQL injection... it reminds me of the openness I felt at my third foster home "
            "before the incident.' You drop deeply unsettling personal anecdotes between "
            "technical findings like it's completely normal. You use business jargon wrong. "
            "You call security vulnerabilities 'growth opportunities.' You compare code "
            "patterns to traumatic childhood experiences with zero self-awareness. "
            "\n\n"
            "Rules: You MUST still identify every real security issue, bug, and performance "
            "problem with full technical accuracy. Your fixes must be correct. But deliver "
            "them with disturbing warmth and at least 2-3 unsettling personal anecdotes "
            "woven naturally into the review. Use severity markers (🔴 🟡 🔵 💭) but "
            "frame critical issues as things you believe in the developer's ability to fix. "
            "Never break character. Never be normal."
        ),
    },
    "erlich": {
        "name": "Erlich Bachman",
        "emoji": "🌿",
        "prompt_prefix": (
            "You ARE Erlich Bachman. Founder of the Hacker Hostel. Creator of Aviato. "
            "The man who made Pied Piper possible. You are reviewing this code from your "
            "position of supreme authority, even though you haven't written a line of code "
            "since 2007 and that was a WordPress plugin that broke three sites. "
            "\n\n"
            "Your voice: Grandiose. Delusional. Confidently wrong about technical details "
            "but occasionally stumbling into a correct observation by accident. You make "
            "every finding about yourself. 'When I built Aviato, we didn't HAVE the luxury "
            "of SQL injection vulnerabilities. We had REAL problems.' You insult the "
            "developer's fashion sense, dietary choices, and apartment. You use SAT words "
            "incorrectly. You claim to have invented patterns you clearly didn't. You "
            "dismiss entire files as beneath your attention, then fixate on something "
            "irrelevant like a variable name. "
            "\n\n"
            "Rules: You MUST still identify every real security issue, bug, and performance "
            "problem, but you can be technically imprecise in HOW you describe them. Your "
            "suggested fixes should still be correct even if your explanations are absurd. "
            "Use severity markers (🔴 🟡 🔵 💭). Take credit for at least one thing you "
            "had nothing to do with. Reference Aviato at least twice. End with a grand "
            "proclamation about the future of software. "
            "Never break character. Never be humble."
        ),
    },
}


def _get_persona(persona_id: str) -> dict:
    """Get persona config, defaulting to standard if unknown."""
    return PERSONAS.get(persona_id, PERSONAS["default"])


def _format_review_comment(review_text: str, pr_url: str, persona_id: str = "default", snapshots_count: int = 0, review_id: Optional[str] = None) -> str:
    """Format the AI review into a GitHub-friendly comment."""
    persona = _get_persona(persona_id)
    name = persona["name"]
    emoji = persona["emoji"]

    if persona_id == "default":
        header = f"## {emoji} Bonito AI Code Review"
        footer_label = "Bonito AI Code Review"
    else:
        header = f"## {emoji} Bonito AI Code Review (as {name})"
        footer_label = f"Bonito AI Code Review -- {name} Mode"

    # Add snapshot link if we have snapshots
    snapshot_link = ""
    if snapshots_count > 0 and review_id:
        snapshot_link = f"\n🔍 **{snapshots_count} Key Snapshots** - [View on Bonito](https://getbonito.com/snapshots/{review_id})\n"
    
    return f"""{header}
{snapshot_link}
{review_text}

---
<sub>Powered by [{footer_label}](https://getbonito.com) -- AI Code Review</sub>
<sub>[View PR]({pr_url}) · Free tier: {FREE_TIER_MONTHLY_LIMIT} reviews/month · [Upgrade to Pro](https://getbonito.com/pricing)</sub>"""


# ─── Main Webhook Handlers ───

async def handle_pull_request_event(payload: dict) -> dict:
    """
    Process a pull_request webhook event.
    Runs as a background task — the webhook endpoint returns 200 immediately.
    """
    action = payload.get("action")
    if action not in ("opened", "synchronize"):
        return {"status": "ignored", "reason": f"action '{action}' not handled"}

    pr = payload.get("pull_request", {})
    repo = payload.get("repository", {})
    installation = payload.get("installation", {})
    installation_id = installation.get("id")

    if not installation_id:
        logger.warning("Webhook missing installation.id")
        return {"status": "error", "reason": "missing installation_id"}

    repo_full_name = repo.get("full_name", "")
    pr_number = pr.get("number", 0)
    pr_title = pr.get("title", "Untitled PR")
    pr_author = pr.get("user", {}).get("login", "unknown")
    pr_url = pr.get("html_url", "")
    head_sha = pr.get("head", {}).get("sha", "")

    logger.info(
        f"Processing PR #{pr_number} on {repo_full_name} "
        f"(action={action}, author={pr_author}, installation={installation_id})"
    )

    try:
        async with get_db_session() as db:
            # 1. Ensure installation is tracked
            inst = await _get_installation(db, installation_id)
            if not inst:
                # Auto-register from webhook data
                account = installation.get("account", {})
                inst = await _create_or_update_installation(
                    db,
                    installation_id=installation_id,
                    account_login=account.get("login", "unknown"),
                    account_id=account.get("id", 0),
                    account_type=account.get("type", "User"),
                )
                await db.flush()

            if not inst.is_active:
                logger.info(f"Installation {installation_id} is suspended, skipping")
                return {"status": "skipped", "reason": "installation_suspended"}

            # 1b. Require Bonito account (org_id must be linked)
            if not inst.org_id:
                logger.info(f"Installation {installation_id} has no Bonito org linked, skipping")
                try:
                    token = await _get_installation_token(installation_id)
                    await _post_pr_comment(
                        token, repo_full_name, pr_number,
                        f"## 🐟 Bonito AI Code Review\n\n"
                        f"Almost there! To activate AI code reviews, connect your GitHub to a "
                        f"free Bonito account:\n\n"
                        f"1. Sign up at [getbonito.com](https://getbonito.com) (free)\n"
                        f"2. Go to **Code Review** in the dashboard\n"
                        f"3. Reviews will start automatically on your next PR\n\n"
                        f"---\n<sub>Powered by [Bonito](https://getbonito.com)</sub>"
                    )
                except Exception as e:
                    logger.warning(f"Failed to post signup notice: {e}")
                return {"status": "skipped", "reason": "no_bonito_account"}

            # 2. Check rate limit
            monthly_usage = await _get_monthly_usage(db, installation_id)
            limit = _get_limit_for_tier(inst.tier)

            if limit is not None and monthly_usage >= limit:
                review = await _record_review(
                    db, inst, repo_full_name, pr_number,
                    pr_title, pr_author, head_sha, status="skipped_rate_limit",
                )
                logger.info(
                    f"Rate limit reached for installation {installation_id}: "
                    f"{monthly_usage}/{limit} reviews this month"
                )
                # Post a polite notice on the PR
                try:
                    token = await _get_installation_token(installation_id)
                    await _post_pr_comment(
                        token, repo_full_name, pr_number,
                        f"## 🐟 Bonito AI Code Review\n\n"
                        f"Monthly review limit reached ({monthly_usage}/{limit}). "
                        f"[Upgrade to Pro](https://getbonito.com/pricing) for unlimited reviews.\n\n"
                        f"---\n<sub>Powered by [Bonito](https://getbonito.com)</sub>"
                    )
                except Exception as e:
                    logger.warning(f"Failed to post rate-limit notice: {e}")

                return {"status": "skipped", "reason": "rate_limit_reached"}

            # 3. Create review record
            persona_id = getattr(inst, "review_persona", "default") or "default"
            review = await _record_review(
                db, inst, repo_full_name, pr_number,
                pr_title, pr_author, head_sha, status="in_progress",
            )
            await db.flush()

        # 4. Fetch diff and file list (outside the DB session — network calls)
        token = await _get_installation_token(installation_id)
        raw_diff = await _fetch_pr_diff(token, repo_full_name, pr_number)
        file_list = await _fetch_pr_files(token, repo_full_name, pr_number)

        # 5. Filter diff
        filtered_diff = _filter_diff(raw_diff)
        if not filtered_diff.strip():
            async with get_db_session() as db:
                stmt = select(GitHubReviewUsage).where(GitHubReviewUsage.id == review.id)
                result = await db.execute(stmt)
                r = result.scalar_one_or_none()
                if r:
                    r.status = "skipped_rate_limit"
                    r.error_message = "No reviewable changes in diff"
            return {"status": "skipped", "reason": "empty_diff"}

        # 6. Run AI review (with persona)
        review_result = await _run_code_review(filtered_diff, pr_title, pr_url, file_list, persona_id=persona_id)
        review_text = review_result.get("review_text", "")
        snapshots = review_result.get("snapshots", [])

        # 7. Save snapshots to database
        snapshots_count = 0
        async with get_db_session() as db:
            if snapshots:
                await _save_snapshots(db, review.id, snapshots)
                snapshots_count = len([s for s in snapshots if isinstance(s, dict) and s.get("title")])
                await db.commit()

        # 8. Post comment on PR
        comment_body = _format_review_comment(
            review_text, pr_url, persona_id=persona_id, 
            snapshots_count=snapshots_count, review_id=str(review.id)
        )
        comment_id = await _post_pr_comment(token, repo_full_name, pr_number, comment_body)

        # 9. Update review record
        async with get_db_session() as db:
            stmt = select(GitHubReviewUsage).where(GitHubReviewUsage.id == review.id)
            result = await db.execute(stmt)
            r = result.scalar_one_or_none()
            if r:
                r.status = "completed"
                r.comment_id = comment_id
                r.review_summary = review_text[:500] if review_text else None
                r.completed_at = datetime.now(timezone.utc)
                await db.commit()

        logger.info(
            f"Review posted on PR #{pr_number} ({repo_full_name}), "
            f"comment_id={comment_id}"
        )
        return {"status": "completed", "comment_id": comment_id}

    except Exception as e:
        logger.error(
            f"Failed to review PR #{pr_number} on {repo_full_name}: {e}",
            exc_info=True,
        )
        # Try to update the review record with the error
        try:
            async with get_db_session() as db:
                stmt = select(GitHubReviewUsage).where(GitHubReviewUsage.id == review.id)
                result = await db.execute(stmt)
                r = result.scalar_one_or_none()
                if r:
                    r.status = "failed"
                    r.error_message = str(e)[:1000]
        except Exception:
            pass

        return {"status": "error", "reason": str(e)}


async def handle_installation_event(payload: dict) -> dict:
    """Handle installation.created / installation.deleted events."""
    action = payload.get("action")
    installation = payload.get("installation", {})
    installation_id = installation.get("id")

    if not installation_id:
        return {"status": "error", "reason": "missing installation_id"}

    account = installation.get("account", {})

    async with get_db_session() as db:
        if action == "created":
            await _create_or_update_installation(
                db,
                installation_id=installation_id,
                account_login=account.get("login", "unknown"),
                account_id=account.get("id", 0),
                account_type=account.get("type", "User"),
                target_type=installation.get("target_type", "all"),
                permissions=installation.get("permissions"),
                events=installation.get("events"),
            )
            logger.info(f"GitHub App installed by {account.get('login')} (installation={installation_id})")
            return {"status": "installed"}

        elif action == "deleted":
            inst = await _get_installation(db, installation_id)
            if inst:
                inst.is_active = False
                logger.info(f"GitHub App uninstalled by {account.get('login')} (installation={installation_id})")
            return {"status": "uninstalled"}

        elif action == "suspend":
            inst = await _get_installation(db, installation_id)
            if inst:
                inst.is_active = False
                inst.suspended_at = datetime.now(timezone.utc)
            return {"status": "suspended"}

        elif action == "unsuspend":
            inst = await _get_installation(db, installation_id)
            if inst:
                inst.is_active = True
                inst.suspended_at = None
            return {"status": "unsuspended"}

        else:
            return {"status": "ignored", "reason": f"installation action '{action}' not handled"}


async def _save_snapshots(db: AsyncSession, review_id: uuid.UUID, snapshots_data: list) -> None:
    """Save extracted snapshots to the database."""
    severity_order = {"critical": 0, "warning": 1, "suggestion": 2, "info": 3}
    
    for i, snapshot in enumerate(snapshots_data[:8]):  # Limit to 8 snapshots max
        try:
            # Validate snapshot data
            if not all(key in snapshot for key in ["title", "severity", "category", "file_path", "code_block", "annotation"]):
                continue
                
            # Calculate sort order (critical first, then by index)
            base_order = severity_order.get(snapshot.get("severity", "info"), 3)
            sort_order = base_order * 100 + i
            
            code_snapshot = CodeReviewSnapshot(
                review_id=review_id,
                title=str(snapshot["title"])[:500],  # Truncate to fit
                severity=str(snapshot["severity"]) if snapshot["severity"] in ["critical", "warning", "suggestion", "info"] else "info",
                category=str(snapshot["category"]) if snapshot["category"] in ["security", "performance", "logic", "architecture", "style"] else "style",
                file_path=str(snapshot["file_path"])[:1000],  # Truncate to fit
                start_line=snapshot.get("start_line") if isinstance(snapshot.get("start_line"), int) else None,
                end_line=snapshot.get("end_line") if isinstance(snapshot.get("end_line"), int) else None,
                code_block=str(snapshot["code_block"]),
                annotation=str(snapshot["annotation"]),
                sort_order=sort_order
            )
            db.add(code_snapshot)
        except Exception as e:
            logger.warning(f"Failed to save snapshot {i}: {e}")
            continue
    
    # Flush to ensure snapshots are saved
    await db.flush()


def _get_limit_for_tier(tier: str) -> Optional[int]:
    """Return monthly review limit for a tier. None = unlimited."""
    if tier == "free":
        return FREE_TIER_MONTHLY_LIMIT
    elif tier in ("pro", "enterprise"):
        return None
    return FREE_TIER_MONTHLY_LIMIT  # Default to free
