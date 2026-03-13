"""
RBAC decorators and dependencies for route-level permission enforcement.
"""
from typing import Callable

from fastapi import Depends

from src.api.auth.jwt_handler import TokenClaims
from src.api.auth.oauth2 import get_current_user
from src.core.exceptions import AuthorizationError

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "session:create", "session:read", "session:delete",
        "agent:spawn", "agent:read", "agent:approve", "agent:deprecate",
        "memory:read", "memory:write", "memory:search",
        "tool:execute",
        "observability:read",
        "tenant:manage",
    },
    "developer": {
        "session:create", "session:read",
        "agent:spawn", "agent:read",
        "memory:read", "memory:write", "memory:search",
        "tool:execute",
        "observability:read",
    },
    "end_user": {
        "session:create", "session:read",
        "agent:read",
        "memory:read", "memory:search",
    },
    "read_only": {
        "session:read",
        "agent:read",
        "memory:read",
    },
}


def has_permission(claims: TokenClaims, permission: str) -> bool:
    role_perms = ROLE_PERMISSIONS.get(claims.role, set())
    return permission in role_perms or permission in claims.scopes


def require_permission(permission: str) -> Callable:
    async def dependency(
        claims: TokenClaims = Depends(get_current_user),
    ) -> TokenClaims:
        if not has_permission(claims, permission):
            raise AuthorizationError(
                f"Role '{claims.role}' lacks permission '{permission}'"
            )
        return claims

    return dependency


def require_role(*allowed_roles: str) -> Callable:
    async def dependency(
        claims: TokenClaims = Depends(get_current_user),
    ) -> TokenClaims:
        if claims.role not in allowed_roles:
            raise AuthorizationError(
                f"Role '{claims.role}' not in allowed roles: {allowed_roles}"
            )
        return claims

    return dependency
