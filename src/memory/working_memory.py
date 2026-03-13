"""
Working Memory: per-agent, per-session short-term memory stored in Redis.
TTL: session end or 30 minutes idle.
"""
from uuid import UUID

import orjson

from src.db.redis_client import redis_client, RedisClient

STM_TTL_SECONDS = 1800  # 30 minutes


class WorkingMemoryStore:
    """Redis-backed working memory (short-term, per session + agent)."""

    async def read(
        self, tenant_id: UUID, session_id: UUID, agent_id: UUID
    ) -> dict | None:
        key = RedisClient.working_memory_key(tenant_id, session_id, agent_id)
        data = await redis_client.client.get(key)
        if data is None:
            return None
        await redis_client.client.expire(key, STM_TTL_SECONDS)
        return orjson.loads(data)

    async def write(
        self, tenant_id: UUID, session_id: UUID, agent_id: UUID, state: dict
    ) -> None:
        key = RedisClient.working_memory_key(tenant_id, session_id, agent_id)
        await redis_client.client.setex(key, STM_TTL_SECONDS, orjson.dumps(state))

    async def update_field(
        self,
        tenant_id: UUID,
        session_id: UUID,
        agent_id: UUID,
        field: str,
        value,
    ) -> None:
        current = await self.read(tenant_id, session_id, agent_id) or {}
        current[field] = value
        await self.write(tenant_id, session_id, agent_id, current)

    async def flush(
        self, tenant_id: UUID, session_id: UUID, agent_id: UUID
    ) -> dict | None:
        """Read and delete working memory. Used at session end to persist to episodic."""
        key = RedisClient.working_memory_key(tenant_id, session_id, agent_id)
        data = await redis_client.client.getdel(key)
        if data is None:
            return None
        return orjson.loads(data)

    async def delete(
        self, tenant_id: UUID, session_id: UUID, agent_id: UUID
    ) -> None:
        key = RedisClient.working_memory_key(tenant_id, session_id, agent_id)
        await redis_client.client.delete(key)


working_memory_store = WorkingMemoryStore()
