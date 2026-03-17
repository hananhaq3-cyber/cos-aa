"""
Dashboard router: aggregate stats for the main dashboard.
GET /api/v1/dashboard/stats
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from src.api.auth.oauth2 import get_current_user
from src.agents.creation.agent_registry import agent_registry
from src.db.postgres import async_session_factory
from src.db.redis_client import redis_client

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats(
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict:
    """Return aggregate platform stats for the dashboard."""
    tenant_id: UUID = request.state.tenant_id

    # Agent counts by status
    agents_by_status: dict[str, int] = {}
    total_agents = 0
    try:
        types = await agent_registry.list_types(tenant_id)
        for t in types:
            status = t.status.value if hasattr(t.status, "value") else str(t.status)
            agents_by_status[status] = agents_by_status.get(status, 0) + 1
            total_agents += 1
    except Exception:
        pass

    # Episodic memory count
    memory_total = 0
    memory_by_tier: dict[str, int] = {}
    try:
        async with async_session_factory() as session:
            await session.execute(
                text("SET app.tenant_id = :tid"), {"tid": str(tenant_id)}
            )
            result = await session.execute(
                text(
                    "SELECT event_type, COUNT(*) FROM episodic_memories "
                    "WHERE tenant_id = :tid GROUP BY event_type"
                ),
                {"tid": str(tenant_id)},
            )
            for row in result.fetchall():
                tier_name = str(row[0])
                count = int(row[1])
                memory_by_tier[tier_name] = count
                memory_total += count
    except Exception:
        pass

    # System health
    health: dict[str, bool] = {}
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        health["postgresql"] = True
    except Exception:
        health["postgresql"] = False

    try:
        await redis_client.client.ping()
        health["redis"] = True
    except Exception:
        health["redis"] = False

    return {
        "agents": {
            "total": total_agents,
            "by_status": agents_by_status,
        },
        "memory": {
            "total": memory_total,
            "by_tier": memory_by_tier,
        },
        "health": {
            "healthy": all(health.values()),
            "checks": health,
        },
    }
