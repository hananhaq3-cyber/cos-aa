"""
Middleware: extract tenant_id from JWT claims and set on request.state.
Also check if token is revoked (blacklisted).
"""
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from src.api.auth.jwt_handler import decode_access_token
from src.api.auth.token_blacklist import is_token_revoked
from src.core.exceptions import AuthenticationError


class TenantContextMiddleware(BaseHTTPMiddleware):

    SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/", "/migrate", "/debug-db", "/cleanup-accounts"}
    # Only skip auth routes that don't require authentication
    SKIP_PREFIXES = (
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/verify-email",
        "/api/v1/auth/me",  # Allow unverified users to check status
        "/api/v1/auth/resend-verification",  # Allow resending verification
        "/api/v1/auth/oauth-verify",  # Allow OAuth verification
        "/api/v1/auth/google",
        "/api/v1/auth/github",
        "/api/v1/auth/apple",
        "/api/v1/observability/health",
    )
    # Core routes that require email verification (soft block)
    VERIFICATION_REQUIRED_PREFIXES = (
        "/api/v1/sessions",
        "/api/v1/agents",
        "/api/v1/memory",
        "/api/v1/observability",
        "/api/v1/admin",
    )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        if path in self.SKIP_PATHS or any(
            path.startswith(p) for p in self.SKIP_PREFIXES
        ):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing or invalid Authorization header"},
                status_code=401,
            )

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            claims = decode_access_token(token)
        except AuthenticationError as e:
            return JSONResponse({"error": e.message}, status_code=401)

        # Check if token is revoked (blacklisted)
        if await is_token_revoked(claims.jti):
            return JSONResponse({"error": "Token has been revoked"}, status_code=401)

        request.state.claims = claims
        request.state.tenant_id = claims.tenant_id
        request.state.user_id = claims.sub
        request.state.role = claims.role

        # Soft block: unverified users cannot access core features
        if not claims.email_verified and any(
            path.startswith(p) for p in self.VERIFICATION_REQUIRED_PREFIXES
        ):
            return JSONResponse(
                {"error": "Email verification required", "code": "EMAIL_NOT_VERIFIED"},
                status_code=403,
            )

        return await call_next(request)
