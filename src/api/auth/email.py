"""Email sending utilities via Resend HTTP API."""
import structlog
import httpx

from src.core.config import settings

logger = structlog.get_logger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


async def send_verification_email(to_email: str, token: str) -> bool:
    """Send verification email via Resend API.

    Returns True on success, False on failure (never raises).
    """
    if not settings.resend_api_key:
        logger.warning("resend_api_key_not_set", msg="Skipping email send")
        return False

    verify_url = f"{settings.frontend_url}/verify-email?token={token}"

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
        <h2 style="color: #60a5fa; margin-bottom: 8px;">Verify your COS-AA email</h2>
        <p style="color: #9ca3af; line-height: 1.6; margin-bottom: 24px;">
            Click the button below to verify your email address.
            This link expires in 24 hours.
        </p>
        <a href="{verify_url}"
           style="display: inline-block; background: #2563eb; color: white;
                  padding: 12px 32px; border-radius: 8px; text-decoration: none;
                  font-weight: 600;">
            Verify Email
        </a>
        <p style="color: #6b7280; font-size: 12px; margin-top: 32px;">
            If you didn't create a COS-AA account, you can safely ignore this email.
        </p>
    </div>
    """

    payload = {
        "from": settings.email_from,
        "to": [to_email],
        "subject": "Verify your COS-AA email address",
        "html": html_body,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                RESEND_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            return True
    except Exception as e:
        logger.error("email_send_failed", to=to_email, error=str(e))
        return False
