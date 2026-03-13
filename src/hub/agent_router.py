"""
Selects the best agent instance for a given task type.
"""
from uuid import UUID

from src.core.domain_objects import AgentType
from src.core.exceptions import AgentNotAvailableError
from src.messaging.grpc_client import AgentStatusResponse, grpc_agent_client

TASK_TYPE_ROUTING: dict[str, AgentType] = {
    "plan": AgentType.PLANNING,
    "schedule": AgentType.PLANNING,
    "workflow": AgentType.PLANNING,
    "learn": AgentType.LEARNING,
    "adapt": AgentType.LEARNING,
    "preference": AgentType.LEARNING,
    "monitor": AgentType.MONITORING,
    "alert": AgentType.MONITORING,
    "track": AgentType.MONITORING,
    "search": AgentType.KNOWLEDGE,
    "retrieve": AgentType.KNOWLEDGE,
    "document": AgentType.KNOWLEDGE,
    "query": AgentType.KNOWLEDGE,
    "research": AgentType.KNOWLEDGE,
}


class AgentRouter:
    """Routes tasks to the most appropriate and least-loaded agent instance."""

    async def select_agent_type(self, task_type: str) -> AgentType:
        for keyword, agent_type in TASK_TYPE_ROUTING.items():
            if keyword in task_type.lower():
                return agent_type
        return AgentType.KNOWLEDGE

    async def select_instance(
        self, agent_type: AgentType
    ) -> AgentStatusResponse:
        instances = await grpc_agent_client.get_all_instances(agent_type.value)
        available = [
            inst
            for inst in instances
            if inst.status.value in ("READY", "BUSY")
            and inst.available_capacity > 0
        ]
        if not available:
            raise AgentNotAvailableError(agent_type.value)
        return min(available, key=lambda i: i.current_task_count)

    async def route(
        self, task_type: str
    ) -> tuple[AgentType, AgentStatusResponse | None]:
        agent_type = await self.select_agent_type(task_type)
        try:
            instance = await self.select_instance(agent_type)
            return agent_type, instance
        except AgentNotAvailableError:
            return agent_type, None


agent_router = AgentRouter()
