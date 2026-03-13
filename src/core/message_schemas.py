"""
Canonical message format for all inter-agent communication.
Every message flowing through the system MUST conform to AgentMessage.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.core.domain_objects import AgentRef, Priority


class MessageType(str, Enum):
    """All message types in the system."""

    # Task lifecycle
    TASK_DISPATCH = "TASK_DISPATCH"
    TASK_RESULT = "TASK_RESULT"
    TASK_FAILURE = "TASK_FAILURE"

    # Agent queries
    STATUS_QUERY = "STATUS_QUERY"
    STATUS_RESPONSE = "STATUS_RESPONSE"
    CAPABILITY_QUERY = "CAPABILITY_QUERY"
    CAPABILITY_RESPONSE = "CAPABILITY_RESPONSE"

    # Memory operations
    MEMORY_REQUEST = "MEMORY_REQUEST"
    MEMORY_RESPONSE = "MEMORY_RESPONSE"

    # Agent lifecycle
    SPAWN_AGENT_REQUEST = "SPAWN_AGENT_REQUEST"
    SPAWN_AGENT_CONFIRMATION = "SPAWN_AGENT_CONFIRMATION"

    # System
    HEARTBEAT = "HEARTBEAT"
    SHUTDOWN = "SHUTDOWN"


class BroadcastRef(BaseModel):
    """Used when a message targets all agents of a type."""

    target_type: str  # e.g., "ALL", "PLANNING", "MONITORING"


class AgentMessage(BaseModel):
    """
    Canonical message schema.
    Every message in the system conforms to this structure.
    """

    message_id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    trace_id: UUID = Field(default_factory=uuid4)
    span_id: UUID = Field(default_factory=uuid4)
    correlation_id: UUID = Field(default_factory=uuid4)

    sender: AgentRef
    recipient: AgentRef | BroadcastRef

    message_type: MessageType
    priority: Priority = Priority.NORMAL
    payload: dict[str, Any] = {}

    created_at: datetime = Field(default_factory=datetime.utcnow)
    ttl_seconds: int = 300
    version: str = "1.0"


# ═══════════════════════════════════════════════════════════════
# TYPED PAYLOADS — one per message_type
# ═══════════════════════════════════════════════════════════════


class TaskDispatchPayload(BaseModel):
    """Payload for TASK_DISPATCH messages: HUB → Agent."""

    task_id: UUID = Field(default_factory=uuid4)
    task_type: str
    goal_id: UUID
    session_id: UUID
    user_id: UUID | None = None
    input_data: dict[str, Any] = {}
    context: dict[str, Any] = {}
    timeout_seconds: int = 60
    idempotency_key: str = Field(default_factory=lambda: str(uuid4()))


class TaskResultPayload(BaseModel):
    """Payload for TASK_RESULT messages: Agent → HUB."""

    task_id: UUID
    success: bool
    output: Any = None
    duration_ms: float = 0.0
    tokens_consumed: int = 0
    tool_calls_made: int = 0


class TaskFailurePayload(BaseModel):
    """Payload for TASK_FAILURE messages: Agent → HUB."""

    task_id: UUID
    error_code: str
    error_message: str
    failure_type: str  # RETRIABLE, NON_RETRIABLE, DEGRADED, CAPABILITY_MISSING
    retry_count: int = 0


class SpawnAgentRequestPayload(BaseModel):
    """Payload for SPAWN_AGENT_REQUEST: HUB → Agent Creation Service."""

    task_type: str
    gap_description: str
    sample_task_ids: list[UUID] = []
    tenant_id: UUID
    require_approval: bool = True


class SpawnAgentConfirmationPayload(BaseModel):
    """Payload for SPAWN_AGENT_CONFIRMATION: Agent Creation → HUB."""

    definition_id: UUID
    agent_type_name: str
    status: str  # VALIDATING, ACTIVE, FAILED


class HeartbeatPayload(BaseModel):
    """Payload for HEARTBEAT messages: Agent → HUB."""

    agent_id: UUID
    current_task_count: int = 0
    max_concurrent_tasks: int = 5
    uptime_seconds: float = 0.0
    healthy: bool = True
