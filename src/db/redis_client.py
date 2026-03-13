"""
Redis connection pool with tenant-namespaced key helpers.
"""
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis

from src.core.config import settings


class RedisClient:
    """Wrapper around redis-py async client with tenant-scoped key utilities."""

    def __init__(self) -> None:
        self._pool: aioredis.ConnectionPool | None = None
        self._client: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=True,
        )
        self._client = aioredis.Redis(connection_pool=self._pool)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> aioredis.Redis:
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client

    # ── Tenant-scoped key builders ──

    @staticmethod
    def tenant_key(tenant_id: UUID, *parts: str) -> str:
        """Build a tenant-namespaced Redis key."""
        suffix = ":".join(parts)
        return f"tenant:{tenant_id}:{suffix}"

    @staticmethod
    def working_memory_key(
        tenant_id: UUID, session_id: UUID, agent_id: UUID
    ) -> str:
        return f"tenant:{tenant_id}:session:{session_id}:agent:{agent_id}:working_memory"

    @staticmethod
    def hub_state_key(tenant_id: UUID, cycle_id: UUID) -> str:
        return f"tenant:{tenant_id}:hub:cycle:{cycle_id}"

    @staticmethod
    def rate_limit_key(tenant_id: UUID, resource: str) -> str:
        return f"tenant:{tenant_id}:rate_limit:{resource}"

    @staticmethod
    def gap_counter_key(tenant_id: UUID, task_type: str) -> str:
        return f"tenant:{tenant_id}:gap:{task_type}:count"

    # ── Convenience wrappers ──

    async def get_json(self, key: str) -> dict | None:
        """Get a key and parse as JSON (via orjson)."""
        import orjson

        val = await self.client.get(key)
        if val is None:
            return None
        return orjson.loads(val)

    async def set_json(
        self, key: str, value: Any, ttl_seconds: int | None = None
    ) -> None:
        """Serialize value as JSON and set with optional TTL."""
        import orjson

        data = orjson.dumps(value)
        if ttl_seconds:
            await self.client.setex(key, ttl_seconds, data)
        else:
            await self.client.set(key, data)


# Singleton instance
redis_client = RedisClient()
