"""
Monitoring Agent: environment watching, system health tracking, deadline
monitoring, and proactive alerting.
"""
from __future__ import annotations

import time
from typing import Any, ClassVar
from uuid import UUID

from src.agents.base_agent import BaseAgent
from src.core.domain_objects import AgentType
from src.core.message_schemas import TaskDispatchPayload, TaskResultPayload
from src.db.redis_client import redis_client


class MonitoringAgent(BaseAgent):
    agent_type: ClassVar[AgentType] = AgentType.MONITORING
    supported_task_types: ClassVar[list[str]] = [
        "health_check",
        "deadline_tracking",
        "resource_monitoring",
        "anomaly_detection",
        "environment_watch",
    ]

    async def execute_task(
        self, task: TaskDispatchPayload
    ) -> TaskResultPayload:
        start = time.perf_counter()
        self._current_task_count += 1

        try:
            task_type = task.task_type

            if task_type == "health_check":
                result = await self._check_system_health(task)
            elif task_type == "deadline_tracking":
                result = await self._track_deadlines(task)
            elif task_type == "resource_monitoring":
                result = await self._monitor_resources(task)
            elif task_type == "anomaly_detection":
                result = await self._detect_anomalies(task)
            elif task_type == "environment_watch":
                result = await self._watch_environment(task)
            else:
                result = {"status": "unknown_task_type", "task_type": task_type}

            elapsed = (time.perf_counter() - start) * 1000
            return TaskResultPayload(
                task_id=task.task_id,
                success=True,
                output=result,
                duration_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return TaskResultPayload(
                task_id=task.task_id,
                success=False,
                output={"error": str(e)},
                duration_ms=elapsed,
            )
        finally:
            self._current_task_count -= 1

    async def _check_system_health(
        self, task: TaskDispatchPayload
    ) -> dict[str, Any]:
        checks: dict[str, Any] = {}

        # Check Redis connectivity
        try:
            await redis_client.client.ping()
            checks["redis"] = {"healthy": True}
        except Exception as e:
            checks["redis"] = {"healthy": False, "error": str(e)}

        # Check active OODA cycles (detect stuck cycles)
        try:
            pattern = "hub:state:*"
            keys = []
            async for key in redis_client.client.scan_iter(
                match=pattern, count=100
            ):
                keys.append(key)
            checks["active_cycles"] = {
                "count": len(keys),
                "healthy": len(keys) < 50,
            }
        except Exception as e:
            checks["active_cycles"] = {"healthy": False, "error": str(e)}

        overall_healthy = all(
            c.get("healthy", False) for c in checks.values()
        )
        return {
            "overall_healthy": overall_healthy,
            "checks": checks,
        }

    async def _track_deadlines(
        self, task: TaskDispatchPayload
    ) -> dict[str, Any]:
        deadlines = task.input_data.get("deadlines", [])
        alerts = []
        for dl in deadlines:
            if dl.get("remaining_seconds", float("inf")) < 300:
                alerts.append(
                    {
                        "deadline": dl.get("name", "unknown"),
                        "remaining_seconds": dl.get("remaining_seconds"),
                        "severity": "HIGH",
                    }
                )
        return {"tracked_deadlines": len(deadlines), "alerts": alerts}

    async def _monitor_resources(
        self, task: TaskDispatchPayload
    ) -> dict[str, Any]:
        info = await redis_client.client.info("memory")
        return {
            "redis_used_memory_mb": round(
                info.get("used_memory", 0) / 1024 / 1024, 2
            ),
            "redis_peak_memory_mb": round(
                info.get("used_memory_peak", 0) / 1024 / 1024, 2
            ),
            "redis_connected_clients": info.get("connected_clients", 0),
        }

    async def _detect_anomalies(
        self, task: TaskDispatchPayload
    ) -> dict[str, Any]:
        metrics = task.input_data.get("metrics", {})
        anomalies = []

        error_rate = metrics.get("error_rate", 0.0)
        if error_rate > 0.1:
            anomalies.append(
                {
                    "metric": "error_rate",
                    "value": error_rate,
                    "threshold": 0.1,
                    "severity": "HIGH" if error_rate > 0.3 else "MEDIUM",
                }
            )

        avg_latency = metrics.get("avg_latency_ms", 0.0)
        if avg_latency > 5000:
            anomalies.append(
                {
                    "metric": "avg_latency_ms",
                    "value": avg_latency,
                    "threshold": 5000,
                    "severity": "MEDIUM",
                }
            )

        return {"anomalies_detected": len(anomalies), "anomalies": anomalies}

    async def _watch_environment(
        self, task: TaskDispatchPayload
    ) -> dict[str, Any]:
        watch_targets = task.input_data.get("targets", [])
        results = []
        for target in watch_targets:
            results.append(
                {
                    "target": target,
                    "status": "monitored",
                    "changes_detected": False,
                }
            )
        return {"watched_targets": len(results), "results": results}


monitoring_agent = MonitoringAgent()
