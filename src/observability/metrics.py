"""
Prometheus metrics registration for COS-AA.
Tracks OODA cycle metrics, agent metrics, memory metrics, and API latency.
"""
from __future__ import annotations

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

# ═══════════════════════════════════════════════════════════════
# SYSTEM INFO
# ═══════════════════════════════════════════════════════════════

system_info = Info("cos_aa", "COS-AA system information")
system_info.info({"version": "2.0.0", "service": "cos-aa"})

# ═══════════════════════════════════════════════════════════════
# OODA CYCLE METRICS
# ═══════════════════════════════════════════════════════════════

ooda_cycles_total = Counter(
    "cos_aa_ooda_cycles_total",
    "Total OODA cycles executed",
    ["tenant_id", "outcome"],  # outcome: success, failed, timeout
)

ooda_cycle_duration_seconds = Histogram(
    "cos_aa_ooda_cycle_duration_seconds",
    "Duration of OODA cycles in seconds",
    ["tenant_id", "phase"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

ooda_iterations_per_cycle = Histogram(
    "cos_aa_ooda_iterations_per_cycle",
    "Number of iterations per OODA cycle",
    ["tenant_id"],
    buckets=[1, 2, 3, 4, 5, 7, 10],
)

active_ooda_cycles = Gauge(
    "cos_aa_active_ooda_cycles",
    "Currently active OODA cycles",
    ["tenant_id"],
)

# ═══════════════════════════════════════════════════════════════
# AGENT METRICS
# ═══════════════════════════════════════════════════════════════

agent_tasks_total = Counter(
    "cos_aa_agent_tasks_total",
    "Total tasks dispatched to agents",
    ["agent_type", "outcome"],
)

agent_task_duration_seconds = Histogram(
    "cos_aa_agent_task_duration_seconds",
    "Duration of agent task execution",
    ["agent_type"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

active_agent_instances = Gauge(
    "cos_aa_active_agent_instances",
    "Currently active agent instances",
    ["agent_type"],
)

agent_spawn_total = Counter(
    "cos_aa_agent_spawn_total",
    "Total agent spawn events",
    ["tenant_id", "outcome"],
)

# ═══════════════════════════════════════════════════════════════
# MEMORY METRICS
# ═══════════════════════════════════════════════════════════════

memory_operations_total = Counter(
    "cos_aa_memory_operations_total",
    "Total memory operations",
    ["tier", "operation"],  # tier: working/episodic/semantic/procedural
)

memory_retrieval_duration_seconds = Histogram(
    "cos_aa_memory_retrieval_duration_seconds",
    "Memory retrieval latency",
    ["tier"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
)

# ═══════════════════════════════════════════════════════════════
# LLM METRICS
# ═══════════════════════════════════════════════════════════════

llm_requests_total = Counter(
    "cos_aa_llm_requests_total",
    "Total LLM API requests",
    ["provider", "outcome"],
)

llm_tokens_consumed = Counter(
    "cos_aa_llm_tokens_consumed",
    "Total LLM tokens consumed",
    ["provider", "token_type"],  # token_type: prompt, completion
)

llm_request_duration_seconds = Histogram(
    "cos_aa_llm_request_duration_seconds",
    "LLM API request duration",
    ["provider"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# ═══════════════════════════════════════════════════════════════
# API METRICS
# ═══════════════════════════════════════════════════════════════

api_requests_total = Counter(
    "cos_aa_api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status_code"],
)

api_request_duration_seconds = Histogram(
    "cos_aa_api_request_duration_seconds",
    "API request duration",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
)

# ═══════════════════════════════════════════════════════════════
# TOOL METRICS
# ═══════════════════════════════════════════════════════════════

tool_executions_total = Counter(
    "cos_aa_tool_executions_total",
    "Total tool executions",
    ["tool_name", "outcome"],
)

tool_execution_duration_seconds = Histogram(
    "cos_aa_tool_execution_duration_seconds",
    "Tool execution duration",
    ["tool_name"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# ═══════════════════════════════════════════════════════════════
# HEARTBEAT & DLQ METRICS
# ═══════════════════════════════════════════════════════════════

agent_heartbeat_stale_total = Counter(
    "cos_aa_agent_heartbeat_stale_total",
    "Total stale agent heartbeats detected",
    ["agent_type"],
)

agent_respawns_total = Counter(
    "cos_aa_agent_respawns_total",
    "Total agent re-spawn events triggered by heartbeat monitor",
    ["agent_type"],
)

dlq_messages_total = Counter(
    "cos_aa_dlq_messages_total",
    "Total messages pushed to the dead-letter queue",
    ["error_type"],
)


def get_metrics() -> bytes:
    """Generate Prometheus metrics output."""
    return generate_latest()
