"""
gRPC client for synchronous agent queries: status, capability check.
Initial implementation uses Redis-backed heartbeat lookup.
"""
from uuid import UUID

from src.core.domain_objects import AgentInstanceStatus


class AgentStatusResponse:
    """Response from an agent's GetStatus query."""

    def __init__(
        self,
        agent_id: UUID,
        agent_type: str,
        current_task_count: int,
        max_concurrent_tasks: int,
        status: AgentInstanceStatus,
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.current_task_count = current_task_count
        self.max_concurrent_tasks = max_concurrent_tasks
        self.status = status

    @property
    def available_capacity(self) -> int:
        return max(0, self.max_concurrent_tasks - self.current_task_count)


class GRPCAgentClient:
    """
    Queries agent instances via Redis heartbeat data.
    Full gRPC will replace this when protobuf stubs are generated.
    """

    def __init__(self):
        from src.db.redis_client import redis_client

        self._redis = redis_client

    async def get_agent_status(
        self, agent_id: UUID, agent_type: str
    ) -> AgentStatusResponse | None:
        key = f"agent:heartbeat:{agent_id}"
        data = await self._redis.get_json(key)
        if data is None:
            return None

        return AgentStatusResponse(
            agent_id=agent_id,
            agent_type=data.get("agent_type", agent_type),
            current_task_count=data.get("current_task_count", 0),
            max_concurrent_tasks=data.get("max_concurrent_tasks", 5),
            status=AgentInstanceStatus(data.get("status", "READY")),
        )

    async def get_all_instances(
        self, agent_type: str
    ) -> list[AgentStatusResponse]:
        pattern = f"agent:heartbeat:{agent_type}:*"
        keys = []
        async for key in self._redis.client.scan_iter(match=pattern):
            keys.append(key)

        instances = []
        for key in keys:
            data = await self._redis.get_json(key)
            if data:
                instances.append(
                    AgentStatusResponse(
                        agent_id=UUID(data["agent_id"]),
                        agent_type=agent_type,
                        current_task_count=data.get("current_task_count", 0),
                        max_concurrent_tasks=data.get(
                            "max_concurrent_tasks", 5
                        ),
                        status=AgentInstanceStatus(
                            data.get("status", "READY")
                        ),
                    )
                )
        return instances


grpc_agent_client = GRPCAgentClient()
