"""
Agent heartbeat sender and stale agent scanner.
Each agent periodically writes a heartbeat key to Redis with a 45s TTL.
A Celery Beat task scans for missing heartbeats and triggers re-spawn.
"""
from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from src.db.redis_client import redis_client

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SECONDS = 15
HEARTBEAT_TTL_SECONDS = 45
HEARTBEAT_KEY_PREFIX = "agent:heartbeat"


class HeartbeatSender:
    """Async background loop that writes heartbeat keys for a running agent."""

    def __init__(self, agent_id: UUID, agent_type: str) -> None:
        self._agent_id = agent_id
        self._agent_type = agent_type
        self._task: asyncio.Task | None = None
        self._running = False

    def _key(self) -> str:
        return f"{HEARTBEAT_KEY_PREFIX}:{self._agent_id}"

    async def _heartbeat_loop(self) -> None:
        while self._running:
            try:
                await redis_client.client.set(
                    self._key(),
                    f"{self._agent_type}",
                    ex=HEARTBEAT_TTL_SECONDS,
                )
                logger.debug(
                    "Heartbeat sent: agent=%s type=%s",
                    self._agent_id,
                    self._agent_type,
                )
            except Exception as e:
                logger.warning("Heartbeat send failed: %s", e)
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)

    def start(self) -> None:
        """Start the heartbeat background loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.ensure_future(self._heartbeat_loop())
        logger.info(
            "Heartbeat started: agent=%s type=%s",
            self._agent_id,
            self._agent_type,
        )

    async def stop(self) -> None:
        """Stop the heartbeat and remove the key."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        # Clean up key on graceful shutdown
        try:
            await redis_client.client.delete(self._key())
        except Exception:
            pass
        logger.info("Heartbeat stopped: agent=%s", self._agent_id)


async def scan_stale_agents(
    known_agent_ids: list[UUID],
) -> list[UUID]:
    """
    Check which agents from the known list have missed their heartbeat.
    Returns list of stale agent IDs that need re-spawn.
    """
    stale: list[UUID] = []
    for agent_id in known_agent_ids:
        key = f"{HEARTBEAT_KEY_PREFIX}:{agent_id}"
        exists = await redis_client.client.exists(key)
        if not exists:
            stale.append(agent_id)
            logger.warning("Stale agent detected: %s", agent_id)
    return stale
