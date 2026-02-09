"""
Email service using Resend for transactional emails.
"""

import os
import resend
from app.core.vault import vault_client

_initialized = False


async def _ensure_initialized():
    global _initialized
    if _initialized:
        return
    # Try vault first, then env var
    api_key = None
    try:
        secrets = await vault_client.get_secrets("integrations/resend")
        api_key = secrets.get("api_key")
    except Exception:
        pass
    api_key = api_key or os.getenv("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY not configured")
    resend.api_key = api_key
    _initialized = True


FRONTEND_URL = os.getenv("FRONTEND_URL", "https://getbonito.com")
FROM_EMAIL = "Bonito <noreply@getbonito.com>"


def _base_template(content: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:40px 20px;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#111111;border-radius:12px;border:1px solid #222;">
<tr><td style="padding:40px 40px 20px;">
  <div style="font-size:24px;font-weight:700;color:#f5f0e8;letter-spacing:-0.5px;">Bonito</div>
</td></tr>
<tr><td style="padding:0 40px 40px;">
  {content}
</td></tr>
<tr><td style="padding:20px 40px;border-top:1px solid #222;">
  <div style="font-size:12px;color:#666;">© Bonito · getbonito.com</div>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _button(url: str, text: str) -> str:
    return f'<a href="{url}" style="display:inline-block;padding:14px 32px;background:#7c3aed;color:#fff;text-decoration:none;border-radius:8px;font-weight:600;font-size:15px;">{text}</a>'


async def send_verification_email(to: str, token: str):
    await _ensure_initialized()
    url = f"{FRONTEND_URL}/verify-email?token={token}"
    html = _base_template(f"""
    <h2 style="color:#f5f0e8;margin:0 0 12px;font-size:20px;">Verify your email</h2>
    <p style="color:#999;font-size:15px;line-height:1.6;margin:0 0 24px;">
      Welcome to Bonito! Click below to verify your email and get started with your unified AI control plane.
    </p>
    <div style="margin:24px 0;">{_button(url, "Verify Email")}</div>
    <p style="color:#666;font-size:13px;margin:16px 0 0;">This link expires in 24 hours. If you didn't create an account, ignore this email.</p>
    """)
    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": [to],
        "subject": "Verify your Bonito account",
        "html": html,
    })


async def send_password_reset_email(to: str, token: str):
    await _ensure_initialized()
    url = f"{FRONTEND_URL}/reset-password?token={token}"
    html = _base_template(f"""
    <h2 style="color:#f5f0e8;margin:0 0 12px;font-size:20px;">Reset your password</h2>
    <p style="color:#999;font-size:15px;line-height:1.6;margin:0 0 24px;">
      We received a request to reset your password. Click below to choose a new one.
    </p>
    <div style="margin:24px 0;">{_button(url, "Reset Password")}</div>
    <p style="color:#666;font-size:13px;margin:16px 0 0;">This link expires in 1 hour. If you didn't request this, ignore this email.</p>
    """)
    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": [to],
        "subject": "Reset your Bonito password",
        "html": html,
    })


async def send_welcome_email(to: str, name: str):
    await _ensure_initialized()
    html = _base_template(f"""
    <h2 style="color:#f5f0e8;margin:0 0 12px;font-size:20px;">Welcome to Bonito, {name}!</h2>
    <p style="color:#999;font-size:15px;line-height:1.6;margin:0 0 24px;">
      Your email has been verified. You're all set to manage your AI infrastructure from a single control plane.
    </p>
    <div style="margin:24px 0;">{_button(f"{FRONTEND_URL}/dashboard", "Go to Dashboard")}</div>
    """)
    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": [to],
        "subject": "Welcome to Bonito 🎉",
        "html": html,
    })
