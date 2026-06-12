"""
Send product update email for OpenRouter + PH launch to production users.
Runs locally with just RESEND_API_KEY — no DB needed.

Usage:
  python scripts/send_openrouter_update.py --test-email hello@trybonito.com
  python scripts/send_openrouter_update.py
"""

import os
import sys
import resend

# ── Recipients (real users only, no test accounts, no Prashant) ───────────

RECIPIENTS = [
    {"name": "Elliot", "email": "ec@elliotcohen.ca"},
    {"name": "Josh", "email": "joshuajohosky@oakandsparrowsystemsenterprise.io"},
    {"name": "Ahmed", "email": "ahmed@webairai.com"},
    {"name": "Madan", "email": "madan@deepux.in"},
    {"name": "Duncan Lane Operations", "email": "ops@duncanlanefinancial.com"},
    {"name": "Abdul", "email": "abdul.hakim@gmail.com"},
    {"name": "Abdul", "email": "abdul.hakim.nasim@gmail.com"},
    {"name": "Anthony", "email": "awarren@nationalcapitalpartnerships.com"},
]

# ── Email content ─────────────────────────────────────────────────────────

FRONTEND_URL = "https://getbonito.com"
LOGO_ICON_URL = f"{FRONTEND_URL}/bonito-icon.png"
FROM_EMAIL = "Bonito <noreply@getbonito.com>"

SUBJECT = "New provider, bigger free tier, and launching on Product Hunt tomorrow"
HEADING = "What's New — May 2026"

ITEMS = [
    {
        "title": "OpenRouter is here — 7 providers, one CLI",
        "description": (
            "You can now connect OpenRouter as a provider, giving you access to hundreds of models "
            "from a single API key. Connect it from the dashboard or the CLI: "
            "<code style='color:#7c3aed;'>bonito providers add openrouter --api-key sk-or-...</code>"
        ),
    },
    {
        "title": "Free tier just got better",
        "description": (
            "We bumped the free tier from 1 provider to 3, and from 1 seat to 3. "
            "You can now experience multi-provider routing and failover without upgrading. "
            "Same 25K requests/month, more room to build."
        ),
    },
    {
        "title": "CLI v0.7.3 — deploy from YAML, connect any provider",
        "description": (
            "The CLI now supports all 7 providers (AWS, Azure, GCP, OpenAI, Anthropic, Groq, OpenRouter) "
            "with <code style='color:#7c3aed;'>bonito providers add</code>. Plus a new "
            "<code style='color:#7c3aed;'>bonito init template</code> command to scaffold your bonito.yaml in seconds. "
            "Upgrade: <code style='color:#7c3aed;'>pip install --upgrade bonito-cli</code>"
        ),
    },
    {
        "title": "Launching on Product Hunt — May 14th",
        "description": (
            "Bonito CLI is launching on Product Hunt tomorrow, May 14th. "
            "If you've been enjoying the platform, we'd really appreciate you checking it out "
            "and sharing your experience. Every bit of support helps."
        ),
    },
]

CTA_TEXT = "See us on Product Hunt"
CTA_URL = "https://www.producthunt.com/posts/bonito-cli"


# ── Template (matches existing email_service.py layout) ───────────────────

def _button(url, text):
    return f'<a href="{url}" style="display:inline-block;padding:14px 32px;background:#7c3aed;color:#fff;text-decoration:none;border-radius:8px;font-weight:600;font-size:15px;letter-spacing:0.3px;">{text}</a>'

def _base_template(content):
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background-color:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0a0a0a;padding:40px 20px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background-color:#111;border:1px solid #1a1a1a;border-radius:12px;overflow:hidden;">

<!-- Header: logo in white circle -->
<tr><td style="padding:40px 40px 28px;border-bottom:1px solid #1a1a1a;" align="center">
  <a href="{FRONTEND_URL}" target="_blank" style="text-decoration:none;">
    <div style="display:inline-block;width:100px;height:100px;border-radius:50%;background-color:#ffffff;text-align:center;line-height:100px;">
      <img src="{LOGO_ICON_URL}" alt="Bonito" width="64" style="display:inline-block;height:auto;max-width:64px;vertical-align:middle;" />
    </div>
  </a>
</td></tr>

<!-- Body -->
<tr><td style="padding:32px 40px;">
  {content}
</td></tr>

<!-- Footer: icon stacked above Bonito text -->
<tr><td style="padding:28px 40px;border-top:1px solid #1a1a1a;" align="center">
  <a href="{FRONTEND_URL}" target="_blank" style="text-decoration:none;display:block;">
    <img src="{LOGO_ICON_URL}" alt="Bonito" width="40" style="display:block;height:auto;max-width:40px;margin:0 auto 8px;" />
    <span style="display:block;font-size:18px;font-weight:700;color:#f5f0e8;letter-spacing:-0.3px;">Bonito</span>
  </a>
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


def build_email(name):
    greeting = f"Hi {name}," if name else "Hi there,"
    items_html = ""
    for item in ITEMS:
        items_html += f"""
        <div style="margin-bottom:20px;padding:16px 20px;background:#0a0a0a;border:1px solid #1a1a1a;border-radius:8px;">
          <p style="color:#f5f0e8;font-size:15px;font-weight:600;margin:0 0 6px;">{item["title"]}</p>
          <p style="color:#999;font-size:14px;line-height:1.6;margin:0;">{item["description"]}</p>
        </div>"""
    return _base_template(f"""
    <h2 style="color:#f5f0e8;margin:0 0 12px;font-size:22px;font-weight:600;">{HEADING}</h2>
    <p style="color:#999;font-size:15px;line-height:1.7;margin:0 0 24px;">
      {greeting} here's what's new in Bonito.
    </p>
    {items_html}
    <div style="margin:28px 0;">{_button(CTA_URL, CTA_TEXT + " →")}</div>
    <p style="color:#555;font-size:12px;margin:16px 0 0;">You're receiving this because you have a Bonito account. Questions? Reply to this email.</p>
    """)


def main():
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        print("ERROR: Set RESEND_API_KEY first")
        sys.exit(1)
    resend.api_key = api_key

    test_email = None
    for i, arg in enumerate(sys.argv):
        if arg == "--test-email" and i + 1 < len(sys.argv):
            test_email = sys.argv[i + 1]

    if test_email:
        print(f"Sending test email to: {test_email}")
        html = build_email("Test")
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [test_email],
            "subject": SUBJECT,
            "html": html,
            "reply_to": "hello@trybonito.com",
        })
        print("Sent!")
        return

    print(f"Sending to {len(RECIPIENTS)} recipients...")
    sent = 0
    errors = 0
    for r in RECIPIENTS:
        try:
            html = build_email(r["name"])
            resend.Emails.send({
                "from": FROM_EMAIL,
                "to": [r["email"]],
                "subject": SUBJECT,
                "html": html,
                "reply_to": "hello@trybonito.com",
            })
            sent += 1
            print(f"  Sent to: {r['email']}")
        except Exception as e:
            errors += 1
            print(f"  FAILED: {r['email']} — {e}")

    print(f"\nDone: {sent} sent, {errors} failed")


if __name__ == "__main__":
    main()
