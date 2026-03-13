"""
JWT token creation and validation.
Claims include: sub (user_id), tenant_id, role, scopes.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt
from pydantic import BaseModel

from src.core.config import settings
from src.core.exceptions import AuthenticationError


class TokenClaims(BaseModel):
    """Decoded JWT claims."""

    sub: UUID
    tenant_id: UUID
    role: str
    scopes: list[str] = []
    exp: datetime
    iat: datetime


def create_access_token(
    user_id: UUID,
    tenant_id: UUID,
    role: str,
    scopes: list[str] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "scopes": scopes or [],
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(
        claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> TokenClaims:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return TokenClaims(
            sub=UUID(payload["sub"]),
            tenant_id=UUID(payload["tenant_id"]),
            role=payload["role"],
            scopes=payload.get("scopes", []),
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
        )
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {e}")
    except (KeyError, ValueError) as e:
        raise AuthenticationError(f"Malformed token claims: {e}")
