"""
Redis-backed token bucket rate limiter, scoped per tenant.
"""
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from src.db.redis_client import redis_client, RedisClient


class RateLimiterMiddleware(BaseHTTPMiddleware):

    SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}
    DEFAULT_LIMIT = 100
    WINDOW_SECONDS = 60

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id is None:
            return await call_next(request)

        window = int(time.time()) // self.WINDOW_SECONDS
        key = RedisClient.rate_limit_key(tenant_id, f"api:{window}")

        client = redis_client.client
        current = await client.incr(key)
        if current == 1:
            await client.expire(key, self.WINDOW_SECONDS + 5)

        if current > self.DEFAULT_LIMIT:
            return JSONResponse(
                {
                    "error": "Rate limit exceeded",
                    "retry_after_seconds": self.WINDOW_SECONDS,
                },
                status_code=429,
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.DEFAULT_LIMIT)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.DEFAULT_LIMIT - current)
        )
        return response
