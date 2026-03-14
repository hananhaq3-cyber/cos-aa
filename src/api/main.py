"""
FastAPI application factory — mounts all routers, middleware, and lifecycle hooks.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.db.postgres import engine
from src.db.redis_client import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    # Startup
    await redis_client.connect()
    await redis_client.client.ping()
    yield
    # Shutdown
    await engine.dispose()
    await redis_client.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="COS-AA — Cognitive Operating System for AI Agents",
        version="2.0.0",
        description="Multi-tenant AI platform with OODA loops and CoT reasoning.",
        lifespan=lifespan,
    )

    # ── CORS ──
    if settings.app_env == "production":
        allowed_origins = [
            f"https://app.{settings.cors_domain}",
            f"https://api.{settings.cors_domain}",
            "https://cos-aa.vercel.app",  # Frontend deployed on Vercel
        ]
    elif settings.app_env == "staging":
        allowed_origins = [
            f"https://app.staging.{settings.cors_domain}",
            f"https://api.staging.{settings.cors_domain}",
            "https://cos-aa.vercel.app",  # Frontend deployed on Vercel
        ]
    else:
        allowed_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Custom Middleware (order matters: outermost first) ──
    from src.api.middleware.request_logger import RequestLoggerMiddleware
    from src.api.middleware.rate_limiter import RateLimiterMiddleware
    from src.api.middleware.tenant_context import TenantContextMiddleware

    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(RateLimiterMiddleware)
    app.add_middleware(TenantContextMiddleware)

    # ── Routers ──
    from src.api.routers import sessions, agents, memory, observability, admin, auth

    app.include_router(auth.router)
    app.include_router(sessions.router)
    app.include_router(agents.router)
    app.include_router(memory.router)
    app.include_router(observability.router)
    app.include_router(admin.router)

    # ── Root health ──
    @app.get("/", tags=["root"])
    async def root():
        return {
            "service": "COS-AA",
            "version": "2.0.0",
            "status": "running",
        }

    @app.get("/health", tags=["root"])
    async def health():
        checks = {}
        try:
            await redis_client.client.ping()
            checks["redis"] = True
        except Exception:
            checks["redis"] = False

        overall = all(checks.values())
        return {"healthy": overall, "checks": checks}

    return app


app = create_app()
