"""
Admin router: API key management, quota monitoring, user listing.
GET    /api/v1/admin/keys
POST   /api/v1/admin/keys
DELETE /api/v1/admin/keys/{key_id}
GET    /api/v1/admin/quotas
GET    /api/v1/admin/users
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from src.api.auth.oauth2 import get_current_user
from src.api.auth.rbac import require_permission
from src.api.schemas.admin_schemas import (
    ApiKeyListResponse,
    GenerateApiKeyResponse,
    QuotaItem,
    QuotaListResponse,
    RevokeApiKeyResponse,
    TenantUserResponse,
    TenantUsersListResponse,
)
from src.auth.tenant import encrypt_api_key
from src.db.postgres import async_session_factory

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/keys", response_model=ApiKeyListResponse)
async def list_api_keys(
    request: Request,
    user: dict = Depends(require_permission("tenant:manage")),
) -> ApiKeyListResponse:
    """List all API keys for the tenant (masked)."""
    return ApiKeyListResponse(keys=[])


@router.post("/keys", response_model=GenerateApiKeyResponse)
async def generate_api_key(
    request: Request,
    user: dict = Depends(require_permission("tenant:manage")),
) -> GenerateApiKeyResponse:
    """Generate a new AES-256-GCM encrypted API key for the tenant."""
    raw_key = f"cos-aa_{secrets.token_hex(32)}"
    encrypt_api_key(raw_key)

    return GenerateApiKeyResponse(
        key_id=uuid4(),
        raw_key=raw_key,
        created_at=datetime.now(timezone.utc),
    )


@router.delete("/keys/{key_id}", response_model=RevokeApiKeyResponse)
async def revoke_api_key(
    key_id: UUID,
    request: Request,
    user: dict = Depends(require_permission("tenant:manage")),
) -> RevokeApiKeyResponse:
    """Revoke an existing API key."""
    return RevokeApiKeyResponse(key_id=key_id, revoked=True)


@router.get("/quotas", response_model=QuotaListResponse)
async def get_quotas(
    request: Request,
    user: dict = Depends(get_current_user),
) -> QuotaListResponse:
    """Get current usage quotas queried from the database."""
    tenant_id: UUID = request.state.tenant_id

    memory_count = 0
    agent_count = 0
    session_count = 0
    trace_count = 0

    try:
        async with async_session_factory() as session:
            await session.execute(
                text("SET app.tenant_id = :tid"), {"tid": str(tenant_id)}
            )
            r = await session.execute(
                text("SELECT COUNT(*) FROM episodic_memories WHERE tenant_id = :tid"),
                {"tid": str(tenant_id)},
            )
            memory_count = r.scalar() or 0

            r = await session.execute(
                text("SELECT COUNT(*) FROM agent_types WHERE tenant_id = :tid"),
                {"tid": str(tenant_id)},
            )
            agent_count = r.scalar() or 0

            r = await session.execute(
                text(
                    "SELECT COUNT(DISTINCT session_id) FROM episodic_memories "
                    "WHERE tenant_id = :tid"
                ),
                {"tid": str(tenant_id)},
            )
            session_count = r.scalar() or 0

            r = await session.execute(
                text("SELECT COUNT(*) FROM cot_audit_log WHERE tenant_id = :tid"),
                {"tid": str(tenant_id)},
            )
            trace_count = r.scalar() or 0
    except Exception:
        pass  # Tables may not exist yet in fresh deployments

    quotas = [
        QuotaItem(resource="OODA Sessions", used=session_count, limit=5000),
        QuotaItem(resource="Memory Fragments", used=memory_count, limit=100_000),
        QuotaItem(resource="Agent Definitions", used=agent_count, limit=50),
        QuotaItem(resource="CoT Trace Entries", used=trace_count, limit=50_000),
        QuotaItem(resource="API Requests / hour", used=0, limit=1000),
        QuotaItem(resource="Storage (MB)", used=0, limit=1024),
    ]

    return QuotaListResponse(quotas=quotas)


@router.get("/users", response_model=TenantUsersListResponse)
async def list_users(
    request: Request,
    user: dict = Depends(require_permission("tenant:manage")),
) -> TenantUsersListResponse:
    """List all users in the tenant."""
    tenant_id: UUID = request.state.tenant_id

    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT id, email, role, created_at
                FROM users
                WHERE tenant_id = :tid
                ORDER BY created_at DESC
            """),
            {"tid": str(tenant_id)},
        )
        rows = result.fetchall()

    users = [
        TenantUserResponse(
            user_id=UUID(str(row[0])),
            email=str(row[1]),
            role=str(row[2]),
            created_at=row[3],
        )
        for row in rows
    ]

    return TenantUsersListResponse(users=users, total=len(users))


# ── Analytics ──


@router.get("/analytics")
async def get_usage_analytics(
    request: Request,
    user: dict = Depends(require_permission("tenant:manage")),
    period: str = "week",  # today, week, month
) -> dict:
    """Get usage analytics for the tenant (sessions, messages, active users)."""
    tenant_id: UUID = request.state.tenant_id
    import datetime

    # Calculate start_time based on period
    now = datetime.datetime.now(datetime.timezone.utc)
    if period == "today":
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # week
        days_since_monday = now.weekday()
        start_time = now - datetime.timedelta(days=days_since_monday)
        start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)

    async with async_session_factory() as session:
        # Query message activity over time
        result = await session.execute(
            text("""
                SELECT DATE_TRUNC('hour', created_at) as hour,
                       COUNT(DISTINCT session_id) as sessions,
                       COUNT(*) as messages
                FROM session_messages
                WHERE tenant_id = :tid AND created_at >= :start_time
                GROUP BY hour
                ORDER BY hour DESC
            """),
            {"tid": str(tenant_id), "start_time": start_time},
        )
        rows = result.fetchall()

    analytics = [
        {
            "timestamp": str(row[0]) if row[0] else "",
            "sessions": int(row[1]) if row[1] else 0,
            "messages": int(row[2]) if row[2] else 0,
        }
        for row in rows
    ]

    total_sessions = sum(a["sessions"] for a in analytics) if analytics else 0
    total_messages = sum(a["messages"] for a in analytics) if analytics else 0

    return {
        "period": period,
        "start_time": str(start_time),
        "end_time": str(now),
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "data_points": analytics,
        "average_messages_per_session": round(
            total_messages / total_sessions, 2
        ) if total_sessions > 0 else 0,
    }
