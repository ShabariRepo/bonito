"""Dynamic access requests router — avoids import chain that breaks agent_engine import.

This module is loaded lazily via app.add_api_route in lifespan startup,
after the app has fully initialized. This bypasses the circular import issue
where bonobot_agents → agent_engine → memwright_service → agent_memory (not installed).
"""

import logging
import secrets
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import require_superadmin
from app.models.user import User

logger = logging.getLogger(__name__)


# ---------- Pydantic Schemas ----------

class AccessRequestSubmit(BaseModel):
    email: EmailStr
    name: str
    company: str | None = None
    use_case: str | None = None


class AccessRequestSubmitResponse(BaseModel):
    message: str


class AccessRequestListItem(BaseModel):
    id: str
    email: str
    name: str
    company: str | None
    use_case: str | None
    status: str
    invite_code: str | None
    created_at: str
    processed_at: str | None
    processed_by: str | None

    class Config:
        from_attributes = True


class AccessRequestApproveDeny(BaseModel):
    action: str  # "approve" or "deny"


class AccessRequestProcessedResponse(BaseModel):
    id: str
    status: str
    invite_code: str | None
    processed_at: str | None


# ---------- Helpers ----------

def _generate_invite_code() -> str:
    return secrets.token_urlsafe(8)[:8].upper()


# ---------- Routes ----------

public_router = APIRouter(tags=["access-requests"])
admin_router = APIRouter(tags=["access-requests-admin"])


@public_router.post("/access-requests", response_model=AccessRequestSubmitResponse, status_code=status.HTTP_201_CREATED)
async def submit_access_request(
    body: AccessRequestSubmit,
    db: AsyncSession = Depends(get_db),
):
    from app.models.access_request import AccessRequest

    result = await db.execute(
        select(AccessRequest).where(
            AccessRequest.email == body.email,
            AccessRequest.status == "pending",
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending access request. We'll be in touch within 24 hours.",
        )

    access_request = AccessRequest(
        email=body.email,
        name=body.name,
        company=body.company,
        use_case=body.use_case,
    )
    db.add(access_request)
    await db.commit()
    await db.refresh(access_request)

    logger.info(f"[ACCESS REQUEST] New request from {body.name} <{body.email}>")

    return AccessRequestSubmitResponse(
        message="Request received. We'll be in touch within 24 hours."
    )


@admin_router.get("/admin/access-requests", response_model=list[AccessRequestListItem])
async def list_access_requests(
    status_filter: str | None = None,
    _admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.access_request import AccessRequest

    query = select(AccessRequest).order_by(AccessRequest.created_at.desc())
    if status_filter:
        query = query.where(AccessRequest.status == status_filter)

    result = await db.execute(query)
    requests = result.scalars().all()

    return [
        AccessRequestListItem(
            id=str(r.id),
            email=r.email,
            name=r.name,
            company=r.company,
            use_case=r.use_case,
            status=r.status,
            invite_code=r.invite_code,
            created_at=r.created_at.isoformat() if r.created_at else None,
            processed_at=r.processed_at.isoformat() if r.processed_at else None,
            processed_by=str(r.processed_by) if r.processed_by else None,
        )
        for r in requests
    ]


@admin_router.patch("/admin/access-requests/{request_id}", response_model=AccessRequestProcessedResponse)
async def process_access_request(
    request_id: str,
    body: AccessRequestApproveDeny,
    admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.access_request import AccessRequest

    if body.action not in ("approve", "deny"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='action must be "approve" or "deny"',
        )

    result = await db.execute(
        select(AccessRequest).where(AccessRequest.id == request_id)
    )
    access_request = result.scalar_one_or_none()
    if not access_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access request not found",
        )

    if access_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is already {access_request.status}",
        )

    now = datetime.now(timezone.utc)
    update_values = {
        "processed_at": now,
        "processed_by": admin.id,
    }

    if body.action == "approve":
        update_values["status"] = "approved"
        update_values["invite_code"] = _generate_invite_code()
    else:
        update_values["status"] = "denied"

    await db.execute(
        update(AccessRequest)
        .where(AccessRequest.id == request_id)
        .values(**update_values)
    )
    await db.commit()

    result = await db.execute(
        select(AccessRequest).where(AccessRequest.id == request_id)
    )
    updated = result.scalar_one()

    # Send invite code email on approval
    if updated.status == "approved" and updated.invite_code:
        try:
            from app.services import email_service
            await email_service.send_invite_code_email(
                updated.email, updated.name, updated.invite_code
            )
            logger.info(f"[ACCESS REQUEST] Invite code email sent to {updated.email}")
        except Exception:
            logger.exception(f"[ACCESS REQUEST] Failed to send invite code email to {updated.email}")

    return AccessRequestProcessedResponse(
        id=str(updated.id),
        status=updated.status,
        invite_code=updated.invite_code,
        processed_at=updated.processed_at.isoformat() if updated.processed_at else None,
    )
