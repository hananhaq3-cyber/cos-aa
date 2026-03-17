"""
Pydantic request/response schemas for session endpoints.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=2000)
    max_iterations: int = Field(default=5, ge=1, le=20)
    timeout_seconds: int = Field(default=120, ge=10, le=600)
    metadata: dict[str, Any] = {}


class CreateSessionResponse(BaseModel):
    session_id: UUID
    tenant_id: UUID
    status: str = "CREATED"
    created_at: datetime


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    message_type: str = "USER"


class MessageResponse(BaseModel):
    message_id: UUID
    session_id: UUID
    role: str
    content: Any
    created_at: datetime


class SessionStateResponse(BaseModel):
    session_id: UUID
    tenant_id: UUID
    status: str
    current_phase: str | None = None
    cycle_count: int = 0
    goal: str = ""
    created_at: datetime
    last_activity: datetime | None = None


class CycleResultResponse(BaseModel):
    cycle_number: int
    goal_achieved: bool
    evidence: str = ""
    phase: str = ""
    duration_ms: float = 0.0


class ConfirmActionRequest(BaseModel):
    approved: bool
    feedback: str | None = None


class ConfirmActionResponse(BaseModel):
    session_id: UUID
    cycle_id: UUID
    approved: bool
    resumed: bool
    message: str = ""


class SessionSummaryResponse(BaseModel):
    session_id: UUID
    tenant_id: UUID
    goal: str = ""
    status: str = "active"
    created_at: datetime
    message_count: int = 0


class SessionListResponse(BaseModel):
    sessions: list[SessionSummaryResponse] = []
    total: int = 0
