"""
Structured JSON logger with automatic trace context injection.
Uses structlog for consistent, machine-readable log output.
"""
from __future__ import annotations

import logging
import sys
from typing import Any
from uuid import UUID

import structlog

from src.core.config import settings


def setup_logging() -> None:
    """Configure structlog for JSON output with trace context."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure standard library logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.getLevelName(settings.log_level.upper()),
    )


def get_logger(name: str = "cos-aa") -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def bind_trace_context(
    trace_id: UUID | str,
    tenant_id: UUID | str | None = None,
    agent_id: UUID | str | None = None,
    session_id: UUID | str | None = None,
) -> None:
    """Bind trace context variables for automatic injection into all logs."""
    structlog.contextvars.clear_contextvars()
    ctx: dict[str, str] = {"trace_id": str(trace_id)}
    if tenant_id:
        ctx["tenant_id"] = str(tenant_id)
    if agent_id:
        ctx["agent_id"] = str(agent_id)
    if session_id:
        ctx["session_id"] = str(session_id)
    structlog.contextvars.bind_contextvars(**ctx)


# Initialize on import
setup_logging()
logger = get_logger()
