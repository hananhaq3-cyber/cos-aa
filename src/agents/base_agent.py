"""
BaseTool abstract interface and BaseAgent abstract interface.
All tools and agents in the system must subclass these.
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.core.domain_objects import (
    AgentType,
    CapabilityDescriptor,
    ExecutionContext,
    HealthStatus,
    ToolResult,
    ValidationResult,
)
from src.core.exceptions import DuplicateTaskError
from src.core.message_schemas import TaskDispatchPayload, TaskResultPayload
from src.messaging.idempotency import IdempotencyGuard
from src.agents.heartbeat import HeartbeatSender

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# BASE TOOL
# ═══════════════════════════════════════════════════════════════


class BaseTool(ABC):
    """Abstract base for all tools available to agents."""

    tool_name: ClassVar[str]
    required_permissions: ClassVar[list[str]] = []
    input_schema: ClassVar[dict] = {}
    output_schema: ClassVar[dict] = {}

    @abstractmethod
    async def execute(
        self, input_data: dict, context: ExecutionContext
    ) -> ToolResult:
        """Execute the tool. context contains tenant_id, trace_id, sandbox_config."""

    def validate_input(self, input_data: dict) -> ValidationResult:
        """Validate input against the tool's input_schema. Override for custom logic."""
        errors: list[str] = []
        for key in self.input_schema.get("required", []):
            if key not in input_data:
                errors.append(f"Missing required field: {key}")
        return ValidationResult(valid=len(errors) == 0, errors=errors)


# ═══════════════════════════════════════════════════════════════
# AGENT STATUS (for status queries)
# ═══════════════════════════════════════════════════════════════


class AgentStatus(BaseModel):
    agent_id: UUID = Field(default_factory=uuid4)
    agent_type: str = ""
    current_task_count: int = 0
    max_concurrent_tasks: int = 5
    status: str = "READY"
    healthy: bool = True


# ═══════════════════════════════════════════════════════════════
# BASE AGENT
# ═══════════════════════════════════════════════════════════════


class BaseAgent(ABC):
    """Abstract base for all agents in the COS-AA system."""

    agent_type: ClassVar[AgentType]
    supported_task_types: ClassVar[list[str]] = []

    def __init__(self) -> None:
        self.agent_id: UUID = uuid4()
        self._current_task_count: int = 0
        self._max_concurrent_tasks: int = 5
        self._tools: dict[str, BaseTool] = {}
        self._heartbeat: HeartbeatSender | None = None

    def start_heartbeat(self) -> None:
        """Start the heartbeat background loop. Call after agent is ready."""
        self._heartbeat = HeartbeatSender(self.agent_id, self.agent_type.value)
        self._heartbeat.start()

    def register_tool(self, tool: BaseTool) -> None:
        self._tools[tool.tool_name] = tool

    def get_tool(self, tool_name: str) -> BaseTool | None:
        return self._tools.get(tool_name)

    @abstractmethod
    async def execute_task(
        self, task: TaskDispatchPayload
    ) -> TaskResultPayload:
        """Main entry point. Must be idempotent (safe to retry)."""

    async def run_task_idempotent(
        self, task: TaskDispatchPayload
    ) -> TaskResultPayload:
        """
        Idempotent wrapper around execute_task().
        Uses Redis SETNX to dedup by idempotency_key.
        Returns cached result on duplicate, executes on first call.
        """
        guard = IdempotencyGuard()
        key = task.idempotency_key

        locked = await guard.check_and_lock(key)
        if not locked:
            cached = await guard.get_cached_result(key)
            if cached is not None:
                logger.info("Returning cached result for %s", key)
                return TaskResultPayload(**cached)
            raise DuplicateTaskError(key)

        try:
            result = await self.execute_task(task)
            await guard.mark_complete(key, result.model_dump(mode="json"))
            return result
        except Exception:
            await guard.release(key)
            raise

    async def get_status(self) -> AgentStatus:
        return AgentStatus(
            agent_id=self.agent_id,
            agent_type=self.agent_type.value,
            current_task_count=self._current_task_count,
            max_concurrent_tasks=self._max_concurrent_tasks,
            status="BUSY"
            if self._current_task_count >= self._max_concurrent_tasks
            else "READY",
        )

    async def get_capabilities(self) -> list[CapabilityDescriptor]:
        return [
            CapabilityDescriptor(
                task_type=tt,
                required_tool_names=list(self._tools.keys()),
            )
            for tt in self.supported_task_types
        ]

    async def health_check(self) -> HealthStatus:
        checks = {"tools_loaded": len(self._tools) > 0}
        return HealthStatus(
            healthy=all(checks.values()),
            checks=checks,
            message="OK" if all(checks.values()) else "Degraded",
        )

    async def on_shutdown(self) -> None:
        """Override to flush working memory and requeue in-flight tasks."""
        if self._heartbeat:
            await self._heartbeat.stop()

    async def _run_tool(
        self, tool_name: str, input_data: dict, context: ExecutionContext
    ) -> ToolResult:
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False, error_message=f"Tool '{tool_name}' not found"
            )
        validation = tool.validate_input(input_data)
        if not validation.valid:
            return ToolResult(
                success=False,
                error_message=f"Validation failed: {'; '.join(validation.errors)}",
            )
        return await tool.execute(input_data, context)
