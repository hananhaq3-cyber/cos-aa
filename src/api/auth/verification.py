"""Email verification token management via Redis."""
import secrets
from uuid import UUID

from src.db.redis_client import redis_client

VERIFY_PREFIX = "email_verify"
COOLDOWN_PREFIX = "email_verify_cooldown"
TOKEN_TTL = 86400       # 24 hours
COOLDOWN_TTL = 60       # 60 seconds between resends


async def create_verification_token(user_id: UUID) -> str:
    """Generate and store a verification token in Redis with 24h TTL."""
    token = secrets.token_urlsafe(32)
    key = f"{VERIFY_PREFIX}:{token}"
    await redis_client.client.setex(key, TOKEN_TTL, str(user_id))
    return token


async def validate_verification_token(token: str) -> UUID | None:
    """Look up token, return user_id if valid, None if expired/invalid."""
    key = f"{VERIFY_PREFIX}:{token}"
    user_id_str = await redis_client.client.get(key)
    if user_id_str is None:
        return None
    await redis_client.client.delete(key)
    return UUID(user_id_str)


async def check_resend_cooldown(user_id: UUID) -> bool:
    """Return True if user is in cooldown (cannot resend yet)."""
    key = f"{COOLDOWN_PREFIX}:{user_id}"
    return await redis_client.client.exists(key) > 0


async def set_resend_cooldown(user_id: UUID) -> None:
    """Set 60-second cooldown for resend requests."""
    key = f"{COOLDOWN_PREFIX}:{user_id}"
    await redis_client.client.setex(key, COOLDOWN_TTL, "1")
