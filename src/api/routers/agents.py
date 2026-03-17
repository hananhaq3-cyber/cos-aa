"""
Agents router: list agents, spawn new agent types, approve/reject.
GET  /api/v1/agents
POST /api/v1/agents/spawn
POST /api/v1/agents/{definition_id}/approve
POST /api/v1/agents/{definition_id}/reject
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.auth.oauth2 import get_current_user
from src.api.auth.rbac import require_permission
from src.api.schemas.agent_schemas import (
    AgentDetailResponse,
    AgentListResponse,
    AgentStatsResponse,
    AgentTypeResponse,
    SpawnAgentRequest,
    SpawnAgentResponse,
)
from src.agents.creation.agent_factory import agent_factory
from src.agents.creation.agent_registry import agent_registry
from src.agents.creation.spawn_service import spawn_service

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.get("", response_model=AgentListResponse)
async def list_agents(
    request: Request,
    user: dict = Depends(get_current_user),
    status: str | None = None,
) -> AgentListResponse:
    """List all registered agent types for the tenant."""
    tenant_id: UUID = request.state.tenant_id

    types = await agent_registry.list_types(tenant_id, status=status)

    agent_type_responses = [
        AgentTypeResponse(
            definition_id=t.definition_id,
            agent_type_name=t.agent_type_name,
            purpose=t.purpose,
            status=t.status.value,
            created_at=t.created_at,
        )
        for t in types
    ]

    return AgentListResponse(
        agent_types=agent_type_responses, total=len(agent_type_responses)
    )


@router.get("/stats", response_model=AgentStatsResponse)
async def get_agent_stats(
    request: Request,
    user: dict = Depends(get_current_user),
) -> AgentStatsResponse:
    """Get agent counts grouped by status."""
    tenant_id: UUID = request.state.tenant_id
    types = await agent_registry.list_types(tenant_id)
    by_status: dict[str, int] = {}
    for t in types:
        s = t.status.value
        by_status[s] = by_status.get(s, 0) + 1
    return AgentStatsResponse(total=len(types), by_status=by_status)


@router.get("/{definition_id}", response_model=AgentDetailResponse)
async def get_agent_detail(
    definition_id: UUID,
    request: Request,
    user: dict = Depends(get_current_user),
) -> AgentDetailResponse:
    """Get full detail for a single agent definition."""
    tenant_id: UUID = request.state.tenant_id
    definition = await agent_registry.get_type(tenant_id, definition_id)
    if definition is None:
        raise HTTPException(status_code=404, detail="Agent definition not found")

    return AgentDetailResponse(
        definition_id=definition.definition_id,
        agent_type_name=definition.agent_type_name,
        purpose=definition.purpose,
        status=definition.status.value,
        system_prompt=definition.system_prompt,
        model_override=definition.model_override,
        trigger_conditions=definition.trigger_conditions,
        tools=[t.model_dump() for t in definition.tools],
        memory_access=definition.memory_access.model_dump(),
        resource_limits=definition.resource_limits.model_dump(),
        created_by=definition.created_by,
        created_at=definition.created_at,
    )


@router.post("/spawn", response_model=SpawnAgentResponse)
async def spawn_agent(
    body: SpawnAgentRequest,
    request: Request,
    user: dict = Depends(require_permission("agent:spawn")),
) -> SpawnAgentResponse:
    """Spawn a new agent type from a capability gap description."""
    tenant_id: UUID = request.state.tenant_id

    try:
        # Generate definition via LLM
        definition = await agent_factory.generate_definition(
            tenant_id=tenant_id,
            gap_description=body.gap_description,
            sample_failures=[{"task_id": str(tid)} for tid in body.sample_task_ids],
        )

        # Validate
        validation = agent_factory.validate_definition(definition)
        if not validation.valid:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Generated definition failed validation",
                    "errors": validation.errors,
                },
            )

        # Submit for approval
        definition = await agent_factory.submit_for_approval(
            definition, require_approval=body.require_approval
        )

        # If auto-approved, spawn immediately
        if not body.require_approval:
            await spawn_service.spawn_agent(definition)

        return SpawnAgentResponse(
            definition_id=definition.definition_id,
            agent_type_name=definition.agent_type_name,
            status=definition.status.value,
            message="Agent definition created"
            + (" and deployed" if not body.require_approval else ", pending approval"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{definition_id}/approve", response_model=AgentTypeResponse)
async def approve_agent(
    definition_id: UUID,
    request: Request,
    user: dict = Depends(require_permission("agent:approve")),
) -> AgentTypeResponse:
    """Approve a VALIDATING agent definition, transitioning it to ACTIVE."""
    tenant_id: UUID = request.state.tenant_id

    definition = await agent_registry.get_type(tenant_id, definition_id)
    if definition is None:
        raise HTTPException(status_code=404, detail="Agent definition not found")

    if definition.status.value != "VALIDATING":
        raise HTTPException(
            status_code=409,
            detail=f"Agent is in state {definition.status.value}, not VALIDATING",
        )

    definition = await agent_registry.update_status(
        tenant_id, definition_id, "ACTIVE"
    )

    # Deploy the newly approved agent
    await spawn_service.spawn_agent(definition)

    return AgentTypeResponse(
        definition_id=definition.definition_id,
        agent_type_name=definition.agent_type_name,
        purpose=definition.purpose,
        status=definition.status.value,
        created_at=definition.created_at,
    )


@router.post("/{definition_id}/reject", response_model=AgentTypeResponse)
async def reject_agent(
    definition_id: UUID,
    request: Request,
    user: dict = Depends(require_permission("agent:approve")),
) -> AgentTypeResponse:
    """Reject a VALIDATING agent definition."""
    tenant_id: UUID = request.state.tenant_id

    definition = await agent_registry.get_type(tenant_id, definition_id)
    if definition is None:
        raise HTTPException(status_code=404, detail="Agent definition not found")

    if definition.status.value != "VALIDATING":
        raise HTTPException(
            status_code=409,
            detail=f"Agent is in state {definition.status.value}, not VALIDATING",
        )

    definition = await agent_registry.update_status(
        tenant_id, definition_id, "REJECTED"
    )

    return AgentTypeResponse(
        definition_id=definition.definition_id,
        agent_type_name=definition.agent_type_name,
        purpose=definition.purpose,
        status=definition.status.value,
        created_at=definition.created_at,
    )
