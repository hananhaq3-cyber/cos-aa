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
from src.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    # Startup
    print("🚀 Starting COS-AA backend...")
    await redis_client.connect()
    await redis_client.client.ping()
    print("✅ Redis connected")
    await init_db()
    print("✅ Database initialized")
    yield
    # Shutdown
    print("🛑 Shutting down COS-AA backend...")
    await engine.dispose()
    await redis_client.close()


def create_app() -> FastAPI:
    # Hide Swagger docs in production
    docs_url = None if settings.app_env == "production" else "/docs"
    redoc_url = None if settings.app_env == "production" else "/redoc"

    app = FastAPI(
        title="COS-AA — Cognitive Operating System for AI Agents",
        version="2.0.0",
        description="Multi-tenant AI platform with OODA loops and CoT reasoning.",
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
    )

    # ── CORS ──
    if settings.app_env == "production":
        allowed_origins = [
            f"https://app.{settings.cors_domain}",
            f"https://api.{settings.cors_domain}",
            "https://cos-aa.vercel.app",  # Production frontend on Vercel
        ]
        # Also allow all Vercel preview deployments during development
        allow_origin_regex = r"https://.*\.vercel\.app"
    elif settings.app_env == "staging":
        allowed_origins = [
            f"https://app.staging.{settings.cors_domain}",
            f"https://api.staging.{settings.cors_domain}",
            "https://cos-aa.vercel.app",
        ]
        allow_origin_regex = r"https://.*\.vercel\.app"
    else:
        allowed_origins = ["*"]
        allow_origin_regex = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins if allow_origin_regex is None else [],
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Custom Middleware (order matters: outermost first) ──
    from src.api.middleware.request_logger import RequestLoggerMiddleware
    from src.api.middleware.rate_limiter import RateLimiterMiddleware
    from src.api.middleware.tenant_context import TenantContextMiddleware
    from src.api.middleware.security_headers import SecurityHeadersMiddleware

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(RateLimiterMiddleware)
    app.add_middleware(TenantContextMiddleware)

    # ── Routers ──
    from src.api.routers import sessions, agents, memory, observability, admin, auth, dashboard

    app.include_router(auth.router)
    app.include_router(dashboard.router)
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
            "version": "2.2.0",
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

    @app.get("/migrate", tags=["root"])
    async def run_migration():
        """One-time migration endpoint to add missing columns."""
        from sqlalchemy import text as sa_text
        results = []
        stmts = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR(32)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider_id VARCHAR(256)",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT false",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ",
            "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS goal TEXT",
        ]
        try:
            async with engine.begin() as conn:
                for stmt in stmts:
                    try:
                        await conn.execute(sa_text(stmt))
                        results.append({"sql": stmt[:50], "status": "ok"})
                    except Exception as e:
                        results.append({"sql": stmt[:50], "status": "error", "error": str(e)})
        except Exception as e:
            return {"status": "connection_error", "error": str(e)}
        return {"status": "done", "results": results}

    @app.get("/debug-db", tags=["root"])
    async def debug_db():
        """Debug: show users table columns and search_path."""
        from sqlalchemy import text as sa_text
        try:
            async with engine.begin() as conn:
                sp = await conn.execute(sa_text("SHOW search_path"))
                search_path = sp.scalar()
                tables = await conn.execute(sa_text(
                    "SELECT table_schema, column_name "
                    "FROM information_schema.columns "
                    "WHERE table_name = 'users' "
                    "ORDER BY table_schema, ordinal_position"
                ))
                cols = [{"schema": r[0], "col": r[1]} for r in tables.fetchall()]
                return {"search_path": search_path, "users_columns": cols}
        except Exception as e:
            return {"error": str(e)}

    return app


app = create_app()
