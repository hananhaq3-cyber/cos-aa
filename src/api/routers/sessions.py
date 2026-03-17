"""
Session router: create sessions, send messages, get state, confirm actions.
POST /api/v1/sessions
GET  /api/v1/sessions
POST /api/v1/sessions/{id}/messages
GET  /api/v1/sessions/{id}/messages
GET  /api/v1/sessions/{id}/state
POST /api/v1/sessions/{id}/confirm
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text as sa_text

from src.api.auth.oauth2 import get_current_user
from src.api.schemas.session_schemas import (
    ConfirmActionRequest,
    ConfirmActionResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    CycleResultResponse,
    MessageResponse,
    SendMessageRequest,
    SessionListResponse,
    SessionStateResponse,
    SessionSummaryResponse,
)
from src.core.domain_objects import OODAPhase
from src.db.postgres import async_session_factory
from src.hub.hub_state import hub_state_manager
from src.hub.ooda_engine import ooda_engine

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    request: Request,
    user: dict = Depends(get_current_user),
    status: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> SessionListResponse:
    """List OODA sessions with optional status/search filtering."""
    tenant_id: UUID = request.state.tenant_id
    user_id: str = user["user_id"]

    async with async_session_factory() as session:
        await session.execute(
            sa_text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)}
        )

        # Build dynamic WHERE clause
        conditions = ["s.tenant_id = :tid", "s.user_id = :uid"]
        params: dict = {"tid": str(tenant_id), "uid": user_id, "lim": limit, "off": offset}

        if status:
            conditions.append("s.status = :status")
            params["status"] = status

        if search:
            conditions.append("s.goal ILIKE :search")
            params["search"] = f"%{search}%"

        where = " AND ".join(conditions)

        # Get sessions with message counts from session_messages
        result = await session.execute(
            sa_text(f"""
                SELECT s.id, s.goal, s.status, s.created_at,
                       COALESCE(mc.cnt, 0) AS message_count
                FROM sessions s
                LEFT JOIN (
                    SELECT session_id, COUNT(*) AS cnt
                    FROM session_messages
                    WHERE tenant_id = :tid
                    GROUP BY session_id
                ) mc ON mc.session_id = s.id
                WHERE {where}
                ORDER BY s.created_at DESC
                LIMIT :lim OFFSET :off
            """),
            params,
        )
        rows = result.fetchall()

        count_result = await session.execute(
            sa_text(f"""
                SELECT COUNT(*) FROM sessions s WHERE {where}
            """),
            params,
        )
        total = count_result.scalar() or 0

    sessions_list = [
        SessionSummaryResponse(
            session_id=row[0],
            tenant_id=tenant_id,
            goal=row[1] or f"Session {str(row[0])[:8]}",
            status=row[2] or "active",
            created_at=row[3],
            message_count=row[4],
        )
        for row in rows
    ]

    return SessionListResponse(sessions=sessions_list, total=total)


@router.post("", response_model=CreateSessionResponse)
async def create_session(
    body: CreateSessionRequest,
    request: Request,
    user: dict = Depends(get_current_user),
) -> CreateSessionResponse:
    """Create a new OODA session and persist it to the database."""
    tenant_id: UUID = request.state.tenant_id
    user_id: str = user["user_id"]
    session_id = uuid4()
    now = datetime.now(timezone.utc)

    async with async_session_factory() as db:
        await db.execute(
            sa_text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)}
        )
        await db.execute(
            sa_text("""
                INSERT INTO sessions (id, tenant_id, user_id, status, goal, created_at, last_active_at)
                VALUES (:sid, :tid, :uid, 'active', :goal, :now, :now)
            """),
            {
                "sid": str(session_id),
                "tid": str(tenant_id),
                "uid": user_id,
                "goal": body.goal,
                "now": now,
            },
        )
        await db.commit()

    return CreateSessionResponse(
        session_id=session_id,
        tenant_id=tenant_id,
        status="active",
        created_at=now,
    )


@router.post(
    "/{session_id}/messages", response_model=CycleResultResponse
)
async def send_message(
    session_id: UUID,
    body: SendMessageRequest,
    request: Request,
    user: dict = Depends(get_current_user),
) -> CycleResultResponse:
    """Send a user message, store it, trigger OODA cycle, store response."""
    tenant_id: UUID = request.state.tenant_id

    # Store user message
    async with async_session_factory() as db:
        await db.execute(
            sa_text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)}
        )
        await db.execute(
            sa_text("""
                INSERT INTO session_messages (tenant_id, session_id, role, content)
                VALUES (:tid, :sid, 'USER', :content)
            """),
            {"tid": str(tenant_id), "sid": str(session_id), "content": body.content},
        )
        # Update session last_active_at
        await db.execute(
            sa_text("""
                UPDATE sessions SET last_active_at = NOW()
                WHERE id = :sid AND tenant_id = :tid
            """),
            {"sid": str(session_id), "tid": str(tenant_id)},
        )
        await db.commit()

    # Run OODA cycle
    try:
        result = await ooda_engine.run_cycle(
            tenant_id=tenant_id,
            session_id=session_id,
            user_message=body.content,
        )

        evidence = result.evidence or "Cycle completed."

        # Store assistant response
        async with async_session_factory() as db:
            await db.execute(
                sa_text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)}
            )
            cot_chain = None
            if result.execution_result:
                import orjson
                cot_chain = orjson.dumps([
                    {"step_id": str(sr.step_id), "success": sr.success, "output": str(sr.output)[:500] if sr.output else None}
                    for sr in result.execution_result.step_results
                ]).decode()

            await db.execute(
                sa_text("""
                    INSERT INTO session_messages (tenant_id, session_id, role, content, cot_chain, trace_id)
                    VALUES (:tid, :sid, 'ASSISTANT', :content, :cot::jsonb, :trace)
                """),
                {
                    "tid": str(tenant_id),
                    "sid": str(session_id),
                    "content": evidence,
                    "cot": cot_chain,
                    "trace": None,
                },
            )
            # Mark session completed if goal achieved
            if result.goal_achieved:
                await db.execute(
                    sa_text("""
                        UPDATE sessions SET status = 'completed', last_active_at = NOW()
                        WHERE id = :sid AND tenant_id = :tid
                    """),
                    {"sid": str(session_id), "tid": str(tenant_id)},
                )
            await db.commit()

        return CycleResultResponse(
            cycle_number=result.cycle_number,
            goal_achieved=result.goal_achieved,
            evidence=evidence,
            phase="COMPLETE" if result.goal_achieved else "REVIEWING",
            duration_ms=result.execution_result.total_duration_ms
            if result.execution_result
            else 0.0,
        )
    except Exception as e:
        # Store error as system message
        try:
            async with async_session_factory() as db:
                await db.execute(
                    sa_text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)}
                )
                await db.execute(
                    sa_text("""
                        INSERT INTO session_messages (tenant_id, session_id, role, content)
                        VALUES (:tid, :sid, 'SYSTEM', :content)
                    """),
                    {"tid": str(tenant_id), "sid": str(session_id), "content": f"Error: {e}"},
                )
                await db.execute(
                    sa_text("""
                        UPDATE sessions SET status = 'failed', last_active_at = NOW()
                        WHERE id = :sid AND tenant_id = :tid
                    """),
                    {"sid": str(session_id), "tid": str(tenant_id)},
                )
                await db.commit()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{session_id}/messages", response_model=list[MessageResponse]
)
async def get_messages(
    session_id: UUID,
    request: Request,
    user: dict = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0,
) -> list[MessageResponse]:
    """Get message history for a session from session_messages table."""
    tenant_id: UUID = request.state.tenant_id

    async with async_session_factory() as db:
        await db.execute(
            sa_text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)}
        )
        result = await db.execute(
            sa_text("""
                SELECT id, session_id, role, content, created_at
                FROM session_messages
                WHERE tenant_id = :tid AND session_id = :sid
                ORDER BY created_at ASC
                LIMIT :lim OFFSET :off
            """),
            {"tid": str(tenant_id), "sid": str(session_id), "lim": limit, "off": offset},
        )
        rows = result.fetchall()

    return [
        MessageResponse(
            message_id=row[0],
            session_id=row[1],
            role=row[2],
            content=row[3],
            created_at=row[4],
        )
        for row in rows
    ]


@router.get(
    "/{session_id}/state", response_model=SessionStateResponse
)
async def get_session_state(
    session_id: UUID,
    request: Request,
    user: dict = Depends(get_current_user),
) -> SessionStateResponse:
    """Get the current state of a session."""
    tenant_id: UUID = request.state.tenant_id

    from src.memory.working_memory import working_memory_store

    # Use a nil UUID as placeholder agent_id for session-level state queries
    placeholder_agent = UUID(int=0)
    state = await working_memory_store.read(tenant_id, session_id, placeholder_agent)

    return SessionStateResponse(
        session_id=session_id,
        tenant_id=tenant_id,
        status=state.get("status", "UNKNOWN") if state else "NO_STATE",
        current_phase=state.get("phase") if state else None,
        cycle_count=int(state.get("cycle_count", 0)) if state else 0,
        goal=state.get("goal", "") if state else "",
        created_at=datetime.now(timezone.utc),
        last_activity=None,
    )


@router.post(
    "/{session_id}/confirm", response_model=ConfirmActionResponse
)
async def confirm_action(
    session_id: UUID,
    body: ConfirmActionRequest,
    request: Request,
    user: dict = Depends(get_current_user),
) -> ConfirmActionResponse:
    """Approve or reject a pending human confirmation request."""
    tenant_id: UUID = request.state.tenant_id

    # Find the paused cycle for this session by scanning Redis
    from src.db.redis_client import redis_client

    pattern = f"hub:state:{tenant_id}:*"
    cycle_state = None
    async for key in redis_client.client.scan_iter(match=pattern):
        data = await redis_client.get_json(key)
        if (
            data
            and data.get("session_id") == str(session_id)
            and data.get("phase") == OODAPhase.AWAITING_CONFIRMATION.value
        ):
            from src.hub.hub_state import CycleState
            cycle_state = CycleState.from_dict(data)
            break

    if cycle_state is None:
        raise HTTPException(
            status_code=404,
            detail="No pending confirmation found for this session",
        )

    if body.approved:
        # Resume the cycle from DECIDING -> ACTING
        await hub_state_manager.transition(cycle_state, OODAPhase.ACTING)
        return ConfirmActionResponse(
            session_id=session_id,
            cycle_id=cycle_state.cycle_id,
            approved=True,
            resumed=True,
            message="Action plan approved. Cycle resumed.",
        )
    else:
        # Reject: mark cycle as failed
        await hub_state_manager.transition(cycle_state, OODAPhase.FAILED)
        await hub_state_manager.delete(tenant_id, cycle_state.cycle_id)
        return ConfirmActionResponse(
            session_id=session_id,
            cycle_id=cycle_state.cycle_id,
            approved=False,
            resumed=False,
            message=f"Action plan rejected. {body.feedback or ''}".strip(),
        )


# ── Export ──


@router.get("/{session_id}/export")
async def export_session(
    session_id: UUID,
    request: Request,
    user: dict = Depends(get_current_user),
    format: str = "json",
) -> dict:
    """Export session messages in CSV, JSON, or Markdown format."""
    tenant_id: UUID = request.state.tenant_id
    import csv
    import json
    from io import StringIO

    # Fetch session messages
    async with async_session_factory() as session:
        await session.execute(sa_text("SET app.tenant_id = :tid"), {"tid": str(tenant_id)})
        result = await session.execute(
            sa_text(
                "SELECT id, role, content, created_at FROM session_messages WHERE session_id = :sid ORDER BY created_at"
            ),
            {"sid": str(session_id)},
        )
        messages = result.fetchall()

    if not messages:
        return {"data": "", "filename": f"session-{session_id}.{format}"}

    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Timestamp", "Role", "Message"])
        for msg in messages:
            writer.writerow([msg[3], msg[1], msg[2]])
        return {"data": output.getvalue(), "filename": f"session-{session_id}.csv"}

    elif format == "markdown":
        lines = [f"# Session {session_id}\n"]
        for msg in messages:
            role_title = msg[1].capitalize()
            timestamp = msg[3]
            content = msg[2]
            lines.append(f"## {role_title} ({timestamp})\n{content}\n")
        return {"data": "\n".join(lines), "filename": f"session-{session_id}.md"}

    else:  # json
        json_data = [
            {
                "timestamp": str(msg[3]),
                "role": msg[1],
                "message": msg[2],
            }
            for msg in messages
        ]
        return {"data": json.dumps(json_data, indent=2), "filename": f"session-{session_id}.json"}
