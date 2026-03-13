"""
Idempotency guard using Redis SETNX with TTL.
Prevents duplicate task execution when messages are retried.
"""
from __future__ import annotations

import logging
from typing import Any

import orjson

from src.db.redis_client import redis_client

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 3600  # 1 hour


class IdempotencyGuard:
    """
    Redis-based idempotency guard.

    Usage:
        guard = IdempotencyGuard()
        locked = await guard.check_and_lock("my-key")
        if not locked:
            return await guard.get_cached_result("my-key")
        # ... do work ...
        await guard.mark_complete("my-key", result)
    """

    KEY_PREFIX = "idempotency"

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds

    def _key(self, idempotency_key: str) -> str:
        return f"{self.KEY_PREFIX}:{idempotency_key}"

    async def check_and_lock(self, idempotency_key: str) -> bool:
        """
        Attempt to acquire an idempotency lock.
        Returns True if the lock was acquired (first execution).
        Returns False if the key already exists (duplicate).
        """
        if not idempotency_key:
            return True  # No key = no dedup

        client = redis_client.client
        acquired = await client.set(
            self._key(idempotency_key),
            orjson.dumps({"status": "PROCESSING"}),
            nx=True,
            ex=self._ttl,
        )
        if acquired:
            logger.debug("Idempotency lock acquired: %s", idempotency_key)
            return True

        logger.info("Duplicate task detected: %s", idempotency_key)
        return False

    async def mark_complete(
        self, idempotency_key: str, result: Any
    ) -> None:
        """Store the result of a completed task for dedup lookups."""
        if not idempotency_key:
            return

        client = redis_client.client
        await client.set(
            self._key(idempotency_key),
            orjson.dumps({"status": "COMPLETE", "result": result}),
            ex=self._ttl,
        )
        logger.debug("Idempotency result cached: %s", idempotency_key)

    async def get_cached_result(self, idempotency_key: str) -> Any | None:
        """Retrieve the cached result for a previously completed task."""
        if not idempotency_key:
            return None

        client = redis_client.client
        raw = await client.get(self._key(idempotency_key))
        if raw is None:
            return None

        data = orjson.loads(raw)
        if data.get("status") == "COMPLETE":
            return data.get("result")

        # Still processing — caller should wait or return a 409
        return None

    async def release(self, idempotency_key: str) -> None:
        """Release a lock (e.g., on failure so the task can be retried)."""
        if not idempotency_key:
            return
        client = redis_client.client
        await client.delete(self._key(idempotency_key))
        logger.debug("Idempotency lock released: %s", idempotency_key)
