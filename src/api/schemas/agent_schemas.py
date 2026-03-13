"""
Pydantic request/response schemas for agent endpoints.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SpawnAgentRequest(BaseModel):
    gap_description: str = Field(..., min_length=10, max_length=2000)
    sample_task_ids: list[UUID] = []
    require_approval: bool = True


class SpawnAgentResponse(BaseModel):
    definition_id: UUID
    agent_type_name: str
    status: str
    message: str


class AgentTypeResponse(BaseModel):
    definition_id: UUID
    agent_type_name: str
    purpose: str
    status: str
    created_at: datetime | None = None


class AgentInstanceResponse(BaseModel):
    agent_id: str
    agent_type: str
    status: str
    current_task_count: int = 0
    max_concurrent_tasks: int = 5


class AgentListResponse(BaseModel):
    agent_types: list[AgentTypeResponse] = []
    total: int = 0
