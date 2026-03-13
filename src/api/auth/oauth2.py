"""
FastAPI dependency that extracts and validates the Bearer token.
"""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.auth.jwt_handler import TokenClaims, decode_access_token
from src.core.exceptions import AuthenticationError

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> TokenClaims:
    if credentials is None:
        raise AuthenticationError("Missing Authorization header")
    return decode_access_token(credentials.credentials)
