"""Audit logging utilities for authentication events."""
import structlog
from uuid import UUID
from src.db.models.audit import AuditEvent
from src.db.postgres import get_session

logger = structlog.get_logger(__name__)


async def log_audit_event(
    tenant_id: UUID | None,
    user_id: UUID | None,
    action: str,
    status: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
    country: str | None = None,
    details: dict | None = None,
) -> None:
    """Log an authentication or security-related event to audit table.

    Args:
        tenant_id: Organization/tenant ID (None for unknown tenant events)
        user_id: User ID (None for login attempts by non-existent users)
        action: Event type (login, logout, failed_login, oauth_login, etc.)
        status: success or failure
        ip_address: Client IP address from request
        user_agent: User-Agent header
        country: Country code derived from IP
        details: Additional context (error_message, oauth_provider, etc.)
    """
    try:
        async with get_session(tenant_id=tenant_id) as session:
            event = AuditEvent(
                tenant_id=tenant_id,
                user_id=user_id,
                action=action,
                status=status,
                ip_address=ip_address,
                user_agent=user_agent,
                country=country,
                details=details or {},
            )
            session.add(event)
            await session.flush()
    except Exception as e:
        # Never let audit logging break the auth flow
        logger.warning("audit_log_failed", action=action, error=str(e))
