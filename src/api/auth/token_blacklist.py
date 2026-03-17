"""
Token revocation and blacklist management via Redis.
When a user logs out, their token JTI is added to the blacklist.
"""
from src.db.redis_client import redis_client


BLACKLIST_PREFIX = "token_blacklist"


async def revoke_token(jti: str, ttl_seconds: int) -> None:
    """Add a token JTI to the blacklist.

    Args:
        jti: The JWT ID to revoke
        ttl_seconds: Time-to-live (should match token expiration time)
    """
    key = f"{BLACKLIST_PREFIX}:{jti}"
    await redis_client.client.setex(key, ttl_seconds, "revoked")


async def is_token_revoked(jti: str) -> bool:
    """Check if a token JTI has been revoked.

    Args:
        jti: The JWT ID to check

    Returns:
        True if token is revoked (blacklisted), False otherwise
    """
    key = f"{BLACKLIST_PREFIX}:{jti}"
    result = await redis_client.client.get(key)
    return result is not None
