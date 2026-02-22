"""
Contact form endpoint — sends submissions to the team via Resend.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.services.email_service import send_contact_notification

router = APIRouter(tags=["contact"])


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    company: str = ""
    message: str


@router.post("/contact", status_code=200)
async def submit_contact(payload: ContactRequest):
    """Receive a contact form submission and email it to the team."""
    try:
        await send_contact_notification(
            name=payload.name,
            email=payload.email,
            company=payload.company,
            message=payload.message,
        )
        return {"ok": True, "message": "Message sent successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to send message. Please try again.")
