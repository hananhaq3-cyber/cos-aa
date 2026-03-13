"""
Dispatches tasks from the HUB to agents via Celery.
"""
from uuid import UUID, uuid4

from celery.result import AsyncResult

from src.core.domain_objects import AgentRef, AgentType, Priority
from src.core.message_schemas import (
    AgentMessage,
    MessageType,
    TaskDispatchPayload,
)
from src.messaging.broker import celery_app

AGENT_QUEUE_MAP: dict[AgentType, str] = {
    AgentType.PLANNING: "planning",
    AgentType.LEARNING: "learning",
    AgentType.MONITORING: "monitoring",
    AgentType.KNOWLEDGE: "knowledge",
    AgentType.CREATED: "creation",
}

PRIORITY_MAP: dict[Priority, int] = {
    Priority.CRITICAL: 0,
    Priority.HIGH: 3,
    Priority.NORMAL: 5,
    Priority.LOW: 9,
}


class TaskDispatcher:
    """Dispatches tasks from HUB to agent workers via Celery."""

    def dispatch_task(
        self,
        tenant_id: UUID,
        agent_type: AgentType,
        payload: TaskDispatchPayload,
        priority: Priority = Priority.NORMAL,
        trace_id: UUID | None = None,
        correlation_id: UUID | None = None,
    ) -> str:
        queue = AGENT_QUEUE_MAP.get(agent_type, "default")

        message = AgentMessage(
            tenant_id=tenant_id,
            trace_id=trace_id or uuid4(),
            correlation_id=correlation_id or uuid4(),
            sender=AgentRef(agent_id=uuid4(), agent_type=AgentType.HUB),
            recipient=AgentRef(agent_id=uuid4(), agent_type=agent_type),
            message_type=MessageType.TASK_DISPATCH,
            priority=priority,
            payload=payload.model_dump(mode="json"),
        )

        task_id = payload.idempotency_key or str(payload.task_id)

        result = celery_app.send_task(
            f"cos_aa.agents.{agent_type.value.lower()}.execute",
            args=[message.model_dump(mode="json")],
            queue=queue,
            priority=PRIORITY_MAP.get(priority, 5),
            task_id=task_id,
            headers={
                "tenant_id": str(tenant_id),
                "trace_id": str(message.trace_id),
            },
        )

        return result.id

    def dispatch_parallel(
        self,
        tasks: list[tuple[UUID, AgentType, TaskDispatchPayload, Priority]],
        correlation_id: UUID | None = None,
    ) -> list[str]:
        cid = correlation_id or uuid4()
        task_ids = []
        for tenant_id, agent_type, payload, priority in tasks:
            tid = self.dispatch_task(
                tenant_id,
                agent_type,
                payload,
                priority,
                correlation_id=cid,
            )
            task_ids.append(tid)
        return task_ids

    def get_result(self, task_id: str, timeout: float = 60.0) -> dict | None:
        result = AsyncResult(task_id, app=celery_app)
        try:
            return result.get(timeout=timeout, propagate=False)
        except Exception:
            return None

    def check_status(self, task_id: str) -> str:
        result = AsyncResult(task_id, app=celery_app)
        return result.status


task_dispatcher = TaskDispatcher()
