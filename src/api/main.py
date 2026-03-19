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
    # Fix: Never use wildcard origins with credentials (browsers reject this)
    # Always use specific origins when allow_credentials=True
    if settings.app_env == "production":
        allowed_origins = [
            "https://cos-aa.vercel.app",  # Production frontend
        ]
        allow_origin_regex = r"https://.*\.vercel\.app"  # Preview deployments
    else:
        # Development/staging: explicit origins (not wildcard)
        allowed_origins = [
            "http://localhost:5173",    # Vite dev server
            "http://localhost:3000",    # Alternative dev port
            "https://cos-aa.vercel.app", # Also allow production in dev
        ]
        allow_origin_regex = r"https://.*\.vercel\.app"

    # ── Custom Middleware ──
    # Order: last added = outermost. CORS MUST be outermost so ALL
    # responses (including 401s from TenantContext) get CORS headers.
    from src.api.middleware.request_logger import RequestLoggerMiddleware
    from src.api.middleware.rate_limiter import RateLimiterMiddleware
    from src.api.middleware.tenant_context import TenantContextMiddleware
    from src.api.middleware.security_headers import SecurityHeadersMiddleware

    app.add_middleware(TenantContextMiddleware)    # innermost
    app.add_middleware(RateLimiterMiddleware)
    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(                            # outermost
        CORSMiddleware,
        allow_origins=allowed_origins if allow_origin_regex is None else [],
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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

    @app.post("/cleanup-accounts", tags=["admin"])
    async def cleanup_all_accounts():
        """DELETE ALL USER ACCOUNTS - Use with extreme caution!"""
        from sqlalchemy import text as sa_text

        # List of tables to clear in dependency order
        delete_statements = [
            "DELETE FROM user_sessions",          # Sessions first
            "DELETE FROM audit_events",          # Audit logs
            "DELETE FROM sessions",              # OODA sessions
            "DELETE FROM cot_audit_log",        # Chain of thought logs
            "DELETE FROM users",                 # Users
            "DELETE FROM tenants",               # Tenants last
        ]

        try:
            async with engine.begin() as conn:
                for stmt in delete_statements:
                    try:
                        result = await conn.execute(sa_text(stmt))
                        print(f"✅ {stmt} - {result.rowcount} rows deleted")
                    except Exception as e:
                        print(f"⚠️  {stmt} - Error: {e}")

                # Reset sequences (PostgreSQL)
                reset_statements = [
                    "ALTER SEQUENCE IF EXISTS users_id_seq RESTART WITH 1",
                    "ALTER SEQUENCE IF EXISTS tenants_id_seq RESTART WITH 1",
                ]
                for stmt in reset_statements:
                    try:
                        await conn.execute(sa_text(stmt))
                    except Exception as e:
                        print(f"⚠️  {stmt} - Error: {e}")

            return {"status": "success", "message": "All accounts deleted successfully"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    return app


app = create_app()
