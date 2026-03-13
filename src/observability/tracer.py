"""
OpenTelemetry tracer setup.
Exports traces to Jaeger via OTLP gRPC.
"""
from __future__ import annotations

from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

from src.core.config import settings

_tracer_provider: TracerProvider | None = None


def setup_tracer() -> TracerProvider:
    """Initialize the OpenTelemetry tracer provider."""
    global _tracer_provider

    if _tracer_provider is not None:
        return _tracer_provider

    resource = Resource.create(
        {
            "service.name": "cos-aa",
            "service.version": "2.0.0",
            "deployment.environment": settings.app_env,
        }
    )

    provider = TracerProvider(resource=resource)

    otlp_endpoint = getattr(settings, "otlp_endpoint", "")
    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    else:
        # Development fallback: log to console
        provider.add_span_processor(
            BatchSpanProcessor(ConsoleSpanExporter())
        )

    trace.set_tracer_provider(provider)
    _tracer_provider = provider
    return provider


def get_tracer(name: str = "cos-aa") -> trace.Tracer:
    """Get an OpenTelemetry tracer instance."""
    if _tracer_provider is None:
        setup_tracer()
    return trace.get_tracer(name)


def instrument_fastapi(app: Any) -> None:
    """Add OpenTelemetry instrumentation to FastAPI."""
    try:
        from opentelemetry.instrumentation.fastapi import (
            FastAPIInstrumentor,
        )

        FastAPIInstrumentor.instrument_app(app)
    except ImportError:
        pass


def instrument_sqlalchemy(engine: Any) -> None:
    """Add OpenTelemetry instrumentation to SQLAlchemy."""
    try:
        from opentelemetry.instrumentation.sqlalchemy import (
            SQLAlchemyInstrumentor,
        )

        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    except ImportError:
        pass


def instrument_redis(client: Any) -> None:
    """Add OpenTelemetry instrumentation to Redis."""
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument()
    except ImportError:
        pass
