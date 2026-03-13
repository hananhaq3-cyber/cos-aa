"""
Redis Pub/Sub for high-frequency monitoring data and real-time OODA progress.
"""
from typing import Awaitable, Callable
from uuid import UUID

import orjson

from src.db.redis_client import redis_client


class PubSubManager:
    """Manages Redis Pub/Sub channels for real-time monitoring data."""

    @staticmethod
    def channel_name(tenant_id: UUID, stream_type: str) -> str:
        return f"tenant:{tenant_id}:stream:{stream_type}"

    async def publish(
        self, tenant_id: UUID, stream_type: str, data: dict
    ) -> int:
        channel = self.channel_name(tenant_id, stream_type)
        payload = orjson.dumps(data)
        return await redis_client.client.publish(channel, payload)

    async def subscribe(
        self,
        tenant_id: UUID,
        stream_type: str,
        handler: Callable[[dict], Awaitable[None]],
    ) -> None:
        channel = self.channel_name(tenant_id, stream_type)
        pubsub = redis_client.client.pubsub()
        await pubsub.subscribe(channel)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = orjson.loads(message["data"])
                    await handler(data)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    async def publish_ooda_progress(
        self,
        tenant_id: UUID,
        session_id: UUID,
        phase: str,
        details: dict | None = None,
    ) -> None:
        await self.publish(
            tenant_id,
            f"session:{session_id}:ooda",
            {"phase": phase, **(details or {})},
        )

    async def publish_confirmation_request(
        self,
        tenant_id: UUID,
        session_id: UUID,
        action_plan: dict,
    ) -> None:
        """Publish a notification that the cycle is awaiting human confirmation."""
        await self.publish(
            tenant_id,
            f"session:{session_id}:confirmation",
            {
                "event": "CONFIRMATION_REQUIRED",
                "session_id": str(session_id),
                "action_plan": action_plan,
            },
        )


pubsub_manager = PubSubManager()
