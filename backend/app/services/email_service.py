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


LOGO_FULL_URL = f"{FRONTEND_URL}/bonito-logo-800.png"  # Full logo with text
LOGO_ICON_URL = f"{FRONTEND_URL}/bonito-icon.png"  # Icon only, no text


def _base_template(content: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background-color:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0a0a0a;padding:40px 20px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:#111;border:1px solid #1a1a1a;border-radius:12px;overflow:hidden;">

<!-- Header: centered large logo -->
<tr><td style="padding:36px 40px 28px;border-bottom:1px solid #1a1a1a;" align="center">
  <a href="{FRONTEND_URL}" target="_blank" style="text-decoration:none;">
    <img src="{LOGO_FULL_URL}" alt="Bonito" width="220" style="display:block;height:auto;max-width:220px;" />
  </a>
</td></tr>

<!-- Body -->
<tr><td style="padding:32px 40px;">
  {content}
</td></tr>

<!-- Footer: icon + Bonito text -->
<tr><td style="padding:28px 40px;border-top:1px solid #1a1a1a;" align="center">
  <a href="{FRONTEND_URL}" target="_blank" style="text-decoration:none;">
    <img src="{LOGO_ICON_URL}" alt="Bonito" width="36" style="display:inline-block;height:auto;max-width:36px;vertical-align:middle;" />
  </a>
  <span style="display:inline-block;vertical-align:middle;margin-left:8px;font-size:18px;font-weight:700;color:#f5f0e8;letter-spacing:-0.3px;">Bonito</span>
  <div style="margin-top:12px;font-size:12px;color:#555;">
    Enterprise AI Control Plane
  </div>
  <div style="margin-top:4px;font-size:12px;">
    <a href="{FRONTEND_URL}" style="color:#7c3aed;text-decoration:none;">getbonito.com</a>
  </div>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""


def _button(url: str, text: str) -> str:
    return f'<a href="{url}" style="display:inline-block;padding:14px 32px;background:#7c3aed;color:#fff;text-decoration:none;border-radius:8px;font-weight:600;font-size:15px;letter-spacing:0.3px;">{text}</a>'


async def send_verification_email(to: str, token: str):
    await _ensure_initialized()
    url = f"{FRONTEND_URL}/verify-email?token={token}"
    html = _base_template(f"""
    <h2 style="color:#f5f0e8;margin:0 0 12px;font-size:22px;font-weight:600;">Verify your email</h2>
    <p style="color:#999;font-size:15px;line-height:1.7;margin:0 0 24px;">
      Welcome to Bonito! Click below to verify your email and get started with your unified AI control plane.
    </p>
    <div style="margin:28px 0;">{_button(url, "Verify Email →")}</div>
    <p style="color:#555;font-size:13px;margin:16px 0 0;">This link expires in 24 hours. If you didn't create an account, ignore this email.</p>
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
    <h2 style="color:#f5f0e8;margin:0 0 12px;font-size:22px;font-weight:600;">Reset your password</h2>
    <p style="color:#999;font-size:15px;line-height:1.7;margin:0 0 24px;">
      We received a request to reset your password. Click below to choose a new one.
    </p>
    <div style="margin:28px 0;">{_button(url, "Reset Password →")}</div>
    <p style="color:#555;font-size:13px;margin:16px 0 0;">This link expires in 1 hour. If you didn't request this, ignore this email.</p>
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
    <h2 style="color:#f5f0e8;margin:0 0 12px;font-size:22px;font-weight:600;">You're verified, {name}! 🎉</h2>
    <p style="color:#999;font-size:15px;line-height:1.7;margin:0 0 24px;">
      Your email has been verified and your Bonito account is ready. Sign in to start managing your AI infrastructure from a single control plane.
    </p>
    <div style="margin:28px 0;">{_button(f"{FRONTEND_URL}/login", "Sign In →")}</div>
    """)
    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": [to],
        "subject": "Email verified — your Bonito account is ready ✅",
        "html": html,
    })
