"""
Observability router: query traces and CoT audit logs.
GET /api/v1/observability/traces/{trace_id}
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text

from src.api.auth.oauth2 import get_current_user
from src.api.auth.rbac import require_permission
from src.db.postgres import async_session_factory

router = APIRouter(prefix="/api/v1/observability", tags=["observability"])


@router.get("/traces/{trace_id}")
async def get_trace(
    trace_id: UUID,
    request: Request,
    user: dict = Depends(require_permission("observability:read")),
) -> dict[str, Any]:
    """Get CoT audit trail for a trace."""
    tenant_id: UUID = request.state.tenant_id

    async with async_session_factory() as session:
        await session.execute(
            text("SET app.tenant_id = :tid"),
            {"tid": str(tenant_id)},
        )

        result = await session.execute(
            text("""
                SELECT id, tenant_id, session_id, cycle_id,
                       phase, cot_chain, created_at
                FROM cot_audit_log
                WHERE tenant_id = :tid
                ORDER BY created_at ASC
                LIMIT 100
            """),
            {"tid": str(tenant_id)},
        )
        rows = result.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="Trace not found")

    entries = [
        {
            "id": str(row[0]),
            "tenant_id": str(row[1]),
            "session_id": str(row[2]),
            "cycle_id": str(row[3]),
            "phase": row[4],
            "cot_chain": row[5],
            "created_at": str(row[6]),
        }
        for row in rows
    ]

    return {
        "trace_id": str(trace_id),
        "tenant_id": str(tenant_id),
        "entries": entries,
        "total": len(entries),
    }


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Basic health check endpoint."""
    return {"status": "healthy"}
