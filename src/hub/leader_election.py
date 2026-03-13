"""
Redis-based leader election for HUB high availability.
Uses SETNX with TTL + Lua scripts for atomic operations.
Only the leader HUB instance processes OODA cycles.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Optional

from src.db.redis_client import redis_client

logger = logging.getLogger(__name__)

LEADER_KEY = "cos_aa:hub:leader"
LEADER_TTL_SECONDS = 30
RENEWAL_INTERVAL_SECONDS = 10

# Lua script: atomic compare-and-delete (release only if we own the lock)
LUA_RELEASE = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

# Lua script: atomic compare-and-expire (renew only if we own the lock)
LUA_RENEW = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("expire", KEYS[1], ARGV[2])
else
    return 0
end
"""


class LeaderElection:
    """
    Redis-based leader election with fencing tokens.

    Usage:
        election = LeaderElection()
        if await election.try_acquire():
            election.start_renewal()
            # ... run cycle ...
            await election.release()
    """

    def __init__(self, instance_id: str | None = None) -> None:
        self._instance_id = instance_id or str(uuid.uuid4())
        self._fencing_token: int = 0
        self._renewal_task: asyncio.Task | None = None
        self._is_leader = False

    @property
    def instance_id(self) -> str:
        return self._instance_id

    @property
    def is_leader(self) -> bool:
        return self._is_leader

    @property
    def fencing_token(self) -> int:
        return self._fencing_token

    async def try_acquire(self) -> bool:
        """
        Attempt to become leader via SETNX.
        Returns True if leadership was acquired.
        """
        client = redis_client.client
        acquired = await client.set(
            LEADER_KEY,
            self._instance_id,
            nx=True,
            ex=LEADER_TTL_SECONDS,
        )
        if acquired:
            self._is_leader = True
            self._fencing_token += 1
            logger.info(
                "Leader election WON: instance=%s token=%d",
                self._instance_id,
                self._fencing_token,
            )
            return True

        # Check if we already own it (e.g., after restart)
        current = await client.get(LEADER_KEY)
        if current and current.decode() == self._instance_id:
            self._is_leader = True
            return True

        logger.debug("Leader election LOST: instance=%s", self._instance_id)
        return False

    async def release(self) -> bool:
        """Release leadership (only if we own it)."""
        client = redis_client.client
        result = await client.eval(
            LUA_RELEASE, 1, LEADER_KEY, self._instance_id
        )
        self._is_leader = False
        if self._renewal_task:
            self._renewal_task.cancel()
            try:
                await self._renewal_task
            except asyncio.CancelledError:
                pass
            self._renewal_task = None

        released = bool(result)
        if released:
            logger.info("Leader released: instance=%s", self._instance_id)
        return released

    async def _renew(self) -> bool:
        """Renew the TTL on our leader lock."""
        client = redis_client.client
        result = await client.eval(
            LUA_RENEW, 1, LEADER_KEY, self._instance_id, str(LEADER_TTL_SECONDS)
        )
        return bool(result)

    async def _renewal_loop(self) -> None:
        """Background loop to keep the leader lock alive."""
        while self._is_leader:
            try:
                renewed = await self._renew()
                if not renewed:
                    logger.warning(
                        "Leader renewal FAILED — lost leadership: instance=%s",
                        self._instance_id,
                    )
                    self._is_leader = False
                    break
            except Exception as e:
                logger.error("Leader renewal error: %s", e)
            await asyncio.sleep(RENEWAL_INTERVAL_SECONDS)

    def start_renewal(self) -> None:
        """Start the background renewal loop."""
        if self._renewal_task is None or self._renewal_task.done():
            self._renewal_task = asyncio.ensure_future(self._renewal_loop())


# Module-level singleton
leader_election = LeaderElection()
