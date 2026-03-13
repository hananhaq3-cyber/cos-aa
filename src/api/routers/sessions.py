"""
Session router: create sessions, send messages, get state, confirm actions.
POST /api/v1/sessions
POST /api/v1/sessions/{id}/messages
GET  /api/v1/sessions/{id}/messages
GET  /api/v1/sessions/{id}/state
POST /api/v1/sessions/{id}/confirm
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.auth.oauth2 import get_current_user
from src.api.auth.rbac import require_permission
from src.api.schemas.session_schemas import (
    ConfirmActionRequest,
    ConfirmActionResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    CycleResultResponse,
    MessageResponse,
    SendMessageRequest,
    SessionStateResponse,
)
from src.core.domain_objects import OODAPhase
from src.hub.hub_state import hub_state_manager
from src.hub.ooda_engine import ooda_engine

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.post("", response_model=CreateSessionResponse)
async def create_session(
    body: CreateSessionRequest,
    request: Request,
    user: dict = Depends(get_current_user),
) -> CreateSessionResponse:
    """Create a new OODA session with a goal."""
    tenant_id: UUID = request.state.tenant_id
    session_id = uuid4()

    return CreateSessionResponse(
        session_id=session_id,
        tenant_id=tenant_id,
        status="CREATED",
        created_at=datetime.now(timezone.utc),
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
    """Send a user message and trigger an OODA cycle."""
    tenant_id: UUID = request.state.tenant_id

    try:
        result = await ooda_engine.run_cycle(
            tenant_id=tenant_id,
            session_id=session_id,
            user_message=body.content,
        )
        return CycleResultResponse(
            cycle_number=result.cycle_number,
            goal_achieved=result.goal_achieved,
            evidence=result.evidence,
            phase="COMPLETE" if result.goal_achieved else "REVIEWING",
            duration_ms=result.execution_result.total_duration_ms
            if result.execution_result
            else 0.0,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{session_id}/messages", response_model=list[MessageResponse]
)
async def get_messages(
    session_id: UUID,
    request: Request,
    user: dict = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
) -> list[MessageResponse]:
    """Get message history for a session."""
    tenant_id: UUID = request.state.tenant_id

    from src.memory.memory_service import memory_service

    episodes = await memory_service.episodic.query_recent(
        tenant_id=str(tenant_id),
        session_id=str(session_id),
        limit=limit,
    )

    messages = []
    for ep in episodes:
        messages.append(
            MessageResponse(
                message_id=uuid4(),
                session_id=session_id,
                role=ep.get("event_type", "SYSTEM"),
                content=ep.get("content", {}),
                created_at=ep.get("created_at", datetime.now(timezone.utc)),
            )
        )

    return messages


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

    from src.memory.working_memory import WorkingMemoryStore

    wm = WorkingMemoryStore()
    state = await wm.read(str(tenant_id), str(session_id))

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
    # In production this would use a session->cycle_id mapping
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
