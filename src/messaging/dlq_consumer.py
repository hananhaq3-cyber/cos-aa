"""
Dead-letter queue consumer.
Reads failed task entries from Redis DLQ, categorizes them, and logs/alerts.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import orjson

from src.db.redis_client import redis_client
from src.observability.metrics import dlq_messages_total

logger = logging.getLogger(__name__)

DLQ_KEY = "cos_aa:dlq"
POLL_INTERVAL_SECONDS = 5

CRITICAL_ERROR_TYPES = {
    "OODATimeoutError",
    "AuthenticationError",
    "AuthorizationError",
    "MemoryWriteError",
    "LLMCallError",
}


class DLQConsumer:
    """
    Consumes entries from the DLQ Redis list.
    Categorizes as critical vs. non-critical and logs at appropriate level.
    """

    def __init__(self, poll_interval: float = POLL_INTERVAL_SECONDS) -> None:
        self._poll_interval = poll_interval
        self._running = False

    def _categorize(self, entry: dict) -> str:
        error_type = entry.get("error_type", "unknown")
        if error_type in CRITICAL_ERROR_TYPES:
            return "critical"
        return "non_critical"

    async def process_entry(self, raw: bytes) -> None:
        """Process a single DLQ entry."""
        try:
            entry = orjson.loads(raw)
        except Exception:
            logger.error("DLQ: unparseable entry: %s", raw[:200])
            return

        category = self._categorize(entry)
        error_type = entry.get("error_type", "unknown")
        dlq_messages_total.labels(error_type=error_type).inc()

        if category == "critical":
            logger.critical(
                "DLQ CRITICAL: task=%s name=%s error=%s at=%s",
                entry.get("task_id"),
                entry.get("task_name"),
                entry.get("error"),
                entry.get("failed_at"),
            )
        else:
            logger.warning(
                "DLQ: task=%s name=%s error=%s at=%s",
                entry.get("task_id"),
                entry.get("task_name"),
                entry.get("error"),
                entry.get("failed_at"),
            )

    async def run(self) -> None:
        """Long-running loop that polls the DLQ."""
        self._running = True
        logger.info("DLQ consumer started (poll_interval=%ss)", self._poll_interval)

        while self._running:
            try:
                raw = await redis_client.client.lpop(DLQ_KEY)
                if raw is not None:
                    await self.process_entry(raw)
                    continue  # Process next immediately if there was an entry
            except Exception as e:
                logger.error("DLQ consumer error: %s", e)

            await asyncio.sleep(self._poll_interval)

        logger.info("DLQ consumer stopped")

    def stop(self) -> None:
        """Signal the consumer to stop."""
        self._running = False
