"""OAuth email verification with temporary codes."""
import secrets
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from src.db.redis_client import redis_client


class OAuthVerificationSession:
    """Temporary OAuth session data before email verification."""

    def __init__(
        self,
        provider: str,
        email: str,
        provider_id: str,
        user_info: Dict[str, Any],
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        is_new_user: bool = True,
    ):
        self.provider = provider
        self.email = email
        self.provider_id = provider_id
        self.user_info = user_info
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.is_new_user = is_new_user
        self.code = self._generate_code()
        self.session_id = self._generate_session_id()
        self.expires_at = datetime.now() + timedelta(minutes=10)  # 10 min expiry

    def _generate_code(self) -> str:
        """Generate 6-digit verification code."""
        return f"{secrets.randbelow(900000) + 100000}"

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return secrets.token_urlsafe(32)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for Redis storage."""
        return {
            "provider": self.provider,
            "email": self.email,
            "provider_id": self.provider_id,
            "user_info": self.user_info,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "is_new_user": self.is_new_user,
            "code": self.code,
            "expires_at": self.expires_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], session_id: str) -> "OAuthVerificationSession":
        """Deserialize from dictionary."""
        session = cls(
            provider=data["provider"],
            email=data["email"],
            provider_id=data["provider_id"],
            user_info=data["user_info"],
            user_id=data.get("user_id"),
            tenant_id=data.get("tenant_id"),
            is_new_user=data.get("is_new_user", True),
        )
        session.code = data["code"]
        session.session_id = session_id
        session.expires_at = datetime.fromisoformat(data["expires_at"])
        return session


async def create_oauth_verification_session(
    provider: str,
    email: str,
    provider_id: str,
    user_info: Dict[str, Any],
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    is_new_user: bool = True,
) -> OAuthVerificationSession:
    """Create temporary OAuth verification session."""
    session = OAuthVerificationSession(
        provider=provider,
        email=email,
        provider_id=provider_id,
        user_info=user_info,
        user_id=user_id,
        tenant_id=tenant_id,
        is_new_user=is_new_user,
    )

    # Store in Redis with 10-minute expiry
    redis_key = f"oauth_verification:{session.session_id}"
    await redis_client.client.setex(
        redis_key,
        600,  # 10 minutes
        json.dumps(session.to_dict()),
    )

    return session


async def get_oauth_verification_session(session_id: str) -> Optional[OAuthVerificationSession]:
    """Get OAuth verification session by ID."""
    redis_key = f"oauth_verification:{session_id}"
    data = await redis_client.client.get(redis_key)

    if not data:
        return None

    try:
        session_data = json.loads(data)
        session = OAuthVerificationSession.from_dict(session_data, session_id)

        # Check if expired
        if session.expires_at < datetime.now():
            await redis_client.client.delete(redis_key)
            return None

        return session
    except (json.JSONDecodeError, KeyError, ValueError):
        await redis_client.client.delete(redis_key)
        return None


async def verify_oauth_code(session_id: str, code: str) -> Optional[OAuthVerificationSession]:
    """Verify OAuth verification code and return session if valid."""
    session = await get_oauth_verification_session(session_id)

    if not session:
        return None

    if session.code != code:
        return None

    # Code is valid, remove from Redis
    redis_key = f"oauth_verification:{session_id}"
    await redis_client.client.delete(redis_key)

    return session


async def delete_oauth_verification_session(session_id: str) -> None:
    """Delete OAuth verification session."""
    redis_key = f"oauth_verification:{session_id}"
    await redis_client.client.delete(redis_key)