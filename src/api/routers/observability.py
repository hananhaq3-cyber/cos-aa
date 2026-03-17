"""
Observability router: query traces, list recent traces, CoT audit logs, health.
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


@router.get("/traces")
async def list_traces(
    request: Request,
    user: dict = Depends(get_current_user),
    limit: int = 50,
) -> dict[str, Any]:
    """List recent traces grouped by session."""
    tenant_id: UUID = request.state.tenant_id

    async with async_session_factory() as session:
        await session.execute(
            text("SET app.tenant_id = :tid"), {"tid": str(tenant_id)}
        )
        result = await session.execute(
            text("""
                SELECT session_id, COUNT(*) AS entry_count,
                       MIN(created_at) AS first_at,
                       MAX(created_at) AS last_at,
                       array_agg(DISTINCT phase) AS phases
                FROM cot_audit_log
                WHERE tenant_id = :tid
                GROUP BY session_id
                ORDER BY MAX(created_at) DESC
                LIMIT :lim
            """),
            {"tid": str(tenant_id), "lim": limit},
        )
        rows = result.fetchall()

    traces = [
        {
            "session_id": str(row[0]),
            "entry_count": row[1],
            "first_at": str(row[2]),
            "last_at": str(row[3]),
            "phases": row[4] or [],
        }
        for row in rows
    ]

    return {"traces": traces, "total": len(traces)}


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
                WHERE tenant_id = :tid AND session_id = :trace_id
                ORDER BY created_at ASC
                LIMIT 100
            """),
            {"tid": str(tenant_id), "trace_id": str(trace_id)},
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
async def health_check() -> dict:
    """Health check with service statuses."""
    checks: dict[str, bool] = {}

    # Check PostgreSQL
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["postgresql"] = True
    except Exception:
        checks["postgresql"] = False

    # Check Redis
    try:
        from src.db.redis_client import redis_client
        await redis_client.client.ping()
        checks["redis"] = True
    except Exception:
        checks["redis"] = False

    healthy = all(checks.values())
    return {"healthy": healthy, "checks": checks}


# ── Export ──


@router.get("/traces/{trace_id}/export", response_model=dict)
async def export_trace(
    trace_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
    format: str = "csv",
) -> dict:
    """Export trace entries as CSV or Markdown."""
    tenant_id: UUID = request.state.tenant_id
    import csv
    from io import StringIO

    async with async_session_factory() as session:
        await session.execute(text("SET app.tenant_id = :tid"), {"tid": str(tenant_id)})
        result = await session.execute(
            text(
                "SELECT id, phase, cot_chain, created_at FROM cot_audit_log "
                "WHERE session_id = :trace_id AND tenant_id = :tid"
            ),
            {"trace_id": trace_id, "tid": str(tenant_id)},
        )
        entries = result.fetchall()

    if not entries:
        return {"data": "", "filename": f"trace-{trace_id}.{format}"}

    if format == "markdown":
        lines = [f"# Trace {trace_id}\n"]
        for entry in entries:
            lines.append(f"## Phase: {entry[1]}\n")
            lines.append(f"**Timestamp:** {entry[3]}\n")
            if entry[2]:
                lines.append(f"**Chain of Thought:**\n```\n{entry[2]}\n```\n")
            lines.append("---\n")
        return {"data": "\n".join(lines), "filename": f"trace-{trace_id}.md"}

    else:  # csv
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Phase", "Chain of Thought", "Timestamp"])
        for entry in entries:
            writer.writerow([entry[1], entry[2], entry[3]])
        return {"data": output.getvalue(), "filename": f"trace-{trace_id}.csv"}
