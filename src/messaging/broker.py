"""
Celery application factory.
Defines task queues (one per agent type + per-tenant overflow).
Includes DLQ failure handler and heartbeat monitor schedule.
"""
import logging

from celery import Celery
from celery.signals import task_failure

from src.core.config import settings

logger = logging.getLogger(__name__)


def create_celery_app() -> Celery:
    app = Celery(
        "cos_aa",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_reject_on_worker_lost=True,
        task_soft_time_limit=300,
        task_time_limit=360,
        result_expires=3600,
        beat_schedule={
            "nightly-memory-consolidation": {
                "task": "cos_aa.memory.consolidation",
                "schedule": 86400.0,
                "args": [],
            },
            "heartbeat-monitor": {
                "task": "cos_aa.agents.heartbeat_monitor",
                "schedule": 30.0,
                "args": [],
            },
        },
        task_routes={
            "cos_aa.agents.planning.*": {"queue": "planning"},
            "cos_aa.agents.learning.*": {"queue": "learning"},
            "cos_aa.agents.monitoring.*": {"queue": "monitoring"},
            "cos_aa.agents.knowledge.*": {"queue": "knowledge"},
            "cos_aa.agents.creation.*": {"queue": "creation"},
            "cos_aa.hub.*": {"queue": "hub"},
            "cos_aa.memory.*": {"queue": "memory"},
        },
        task_default_queue="default",
    )

    return app


celery_app = create_celery_app()

DLQ_KEY = "cos_aa:dlq"
DLQ_MAX_SIZE = 10_000


@task_failure.connect
def on_task_failure(sender=None, task_id=None, exception=None, **kwargs):
    """Push failed task info to the DLQ Redis list."""
    import json
    from datetime import datetime, timezone

    try:
        from src.db.redis_client import redis_client as _rc

        entry = json.dumps({
            "task_id": str(task_id),
            "task_name": sender.name if sender else "unknown",
            "error": str(exception),
            "error_type": type(exception).__name__ if exception else "unknown",
            "failed_at": datetime.now(timezone.utc).isoformat(),
        })
        pipe = _rc.client.pipeline()
        pipe.rpush(DLQ_KEY, entry)
        pipe.ltrim(DLQ_KEY, -DLQ_MAX_SIZE, -1)
        pipe.execute()
    except Exception as e:
        logger.error("Failed to push to DLQ: %s", e)
