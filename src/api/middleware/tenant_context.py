"""
Middleware: extract tenant_id from JWT claims and set on request.state.
"""
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from src.api.auth.jwt_handler import decode_access_token
from src.core.exceptions import AuthenticationError


class TenantContextMiddleware(BaseHTTPMiddleware):

    SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/"}
    SKIP_PREFIXES = ("/api/v1/auth",)

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

        request.state.claims = claims
        request.state.tenant_id = claims.tenant_id
        request.state.user_id = claims.sub
        request.state.role = claims.role

        return await call_next(request)
