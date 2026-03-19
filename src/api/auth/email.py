"""Email sending utilities via Resend HTTP API or Gmail SMTP (free fallback)."""
import structlog
import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.core.config import settings

logger = structlog.get_logger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


async def send_oauth_verification_email(to_email: str, code: str, provider: str) -> bool:
    """Send OAuth verification code email.

    Returns True on success, False on failure (never raises).
    """

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
        <h2 style="color: #60a5fa; margin-bottom: 8px;">Verify your {provider.title()} sign-in</h2>
        <p style="color: #9ca3af; line-height: 1.6; margin-bottom: 24px;">
            To complete your sign-in with {provider.title()}, please enter this verification code:
        </p>
        <div style="background: #1f2937; border: 1px solid #374151; border-radius: 8px; padding: 24px; text-align: center; margin-bottom: 24px;">
            <div style="font-size: 32px; font-weight: bold; color: #60a5fa; letter-spacing: 8px; font-family: monospace;">
                {code}
            </div>
            <p style="color: #6b7280; font-size: 14px; margin-top: 12px;">
                This code expires in 10 minutes
            </p>
        </div>
        <p style="color: #9ca3af; line-height: 1.6; margin-bottom: 16px;">
            If you didn't try to sign in to COS-AA, you can safely ignore this email.
        </p>
        <p style="color: #6b7280; font-size: 12px;">
            For your security, never share this code with anyone.
        </p>
    </div>
    """

    # Try Resend first (if configured)
    if settings.resend_api_key:
        logger.info("sending_oauth_code_via_resend", to=to_email, provider=provider)
        if await _send_oauth_code_via_resend(to_email, html_body, provider):
            return True
        else:
            logger.warning("resend_failed_trying_smtp", to=to_email)

    # Fallback to Gmail SMTP (free)
    if settings.smtp_user and settings.smtp_password:
        logger.info("sending_oauth_code_via_gmail_smtp", to=to_email, provider=provider)
        return await _send_oauth_code_via_smtp(to_email, html_body, provider)
    else:
        logger.error("no_email_configuration", msg="Neither Resend API key nor SMTP credentials configured")
        return False


async def _send_oauth_code_via_resend(to_email: str, html_body: str, provider: str) -> bool:
    """Send OAuth verification code via Resend API."""
    payload = {
        "from": settings.email_from,
        "to": [to_email],
        "subject": f"Your COS-AA {provider.title()} verification code",
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
        logger.error("resend_oauth_code_send_failed", to=to_email, error=str(e))
        return False


async def _send_oauth_code_via_smtp(to_email: str, html_body: str, provider: str) -> bool:
    """Send OAuth verification code via Gmail SMTP."""
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Your COS-AA {provider.title()} verification code"
        msg['From'] = settings.smtp_user
        msg['To'] = to_email

        # Add HTML content
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)

        # Send via Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)

        return True
    except Exception as e:
        logger.error("smtp_oauth_code_send_failed", to=to_email, error=str(e))
        return False


async def send_verification_email(to_email: str, token: str) -> bool:
    """Send verification email via Resend API or Gmail SMTP (free fallback).

    Returns True on success, False on failure (never raises).
    """
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

    # Try Resend first (if configured)
    if settings.resend_api_key:
        logger.info("sending_email_via_resend", to=to_email)
        if await _send_via_resend(to_email, html_body):
            return True
        else:
            logger.warning("resend_failed_trying_smtp", to=to_email)

    # Fallback to Gmail SMTP (free)
    if settings.smtp_user and settings.smtp_password:
        logger.info("sending_email_via_gmail_smtp", to=to_email)
        return await _send_via_smtp(to_email, html_body)
    else:
        logger.error("no_email_configuration", msg="Neither Resend API key nor SMTP credentials configured")
        return False


async def _send_via_resend(to_email: str, html_body: str) -> bool:
    """Send email via Resend API."""
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
        logger.error("resend_email_send_failed", to=to_email, error=str(e))
        return False


async def _send_via_smtp(to_email: str, html_body: str) -> bool:
    """Send email via Gmail SMTP (free alternative)."""
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Verify your COS-AA email address"
        msg['From'] = settings.smtp_user
        msg['To'] = to_email

        # Add HTML content
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)

        # Send via Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)

        return True
    except Exception as e:
        logger.error("smtp_email_send_failed", to=to_email, error=str(e))
        return False
