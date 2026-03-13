"""
ACT phase: resolve dependency DAG, dispatch steps to agents, track execution.
"""
import asyncio
import time
from uuid import UUID

from src.core.domain_objects import (
    ActionPlan,
    ActionStep,
    ExecutionResult,
    Priority,
    StepResult,
)
from src.core.message_schemas import TaskDispatchPayload
from src.messaging.dispatcher import task_dispatcher
from src.messaging.pubsub import pubsub_manager


class ActPhase:
    """Execute the action plan by dispatching steps to agents."""

    async def execute(
        self,
        tenant_id: UUID,
        session_id: UUID,
        plan: ActionPlan,
        trace_id: UUID,
    ) -> ExecutionResult:
        step_results: list[StepResult] = []
        completed_step_ids: set[UUID] = set()
        start_time = time.perf_counter()

        pending = list(plan.steps)

        while pending:
            ready = [
                step
                for step in pending
                if all(
                    dep_id in completed_step_ids for dep_id in step.depends_on
                )
            ]

            if not ready:
                break

            dispatch_tasks = []
            for step in ready:
                dispatch_tasks.append(
                    self._dispatch_step(
                        tenant_id, session_id, step, plan.goal_id, trace_id
                    )
                )

            results = await asyncio.gather(
                *dispatch_tasks, return_exceptions=True
            )

            for step, result in zip(ready, results):
                if isinstance(result, Exception):
                    sr = StepResult(
                        step_id=step.step_id,
                        success=False,
                        error_message=str(result),
                    )
                else:
                    sr = result

                step_results.append(sr)
                completed_step_ids.add(step.step_id)
                pending.remove(step)

                if not sr.success and step.is_critical:
                    for remaining in pending:
                        step_results.append(StepResult(
                            step_id=remaining.step_id,
                            success=False,
                            error_message="Aborted: critical preceding step failed",
                        ))
                    pending.clear()
                    break

        total_duration = (time.perf_counter() - start_time) * 1000
        all_critical_ok = all(
            sr.success
            for sr in step_results
            if any(
                s.step_id == sr.step_id and s.is_critical for s in plan.steps
            )
        )

        return ExecutionResult(
            plan_id=plan.plan_id,
            step_results=step_results,
            all_critical_succeeded=all_critical_ok,
            total_duration_ms=total_duration,
        )

    async def _dispatch_step(
        self,
        tenant_id: UUID,
        session_id: UUID,
        step: ActionStep,
        goal_id: UUID,
        trace_id: UUID,
    ) -> StepResult:
        start = time.perf_counter()

        payload = TaskDispatchPayload(
            task_id=step.step_id,
            task_type=step.agent_type.value.lower(),
            goal_id=goal_id,
            session_id=session_id,
            input_data=step.input_params,
            timeout_seconds=step.timeout_seconds,
            idempotency_key=str(step.step_id),
        )

        await pubsub_manager.publish_ooda_progress(
            tenant_id,
            session_id,
            "ACTING",
            {
                "agent_type": step.agent_type.value,
                "step_id": str(step.step_id),
            },
        )

        task_id = task_dispatcher.dispatch_task(
            tenant_id, step.agent_type, payload, trace_id=trace_id
        )

        result = task_dispatcher.get_result(
            task_id, timeout=step.timeout_seconds
        )
        duration = (time.perf_counter() - start) * 1000

        if result is None:
            return StepResult(
                step_id=step.step_id,
                success=False,
                error_message="Timeout waiting for agent result",
                duration_ms=duration,
            )

        return StepResult(
            step_id=step.step_id,
            success=result.get("success", False),
            output=result.get("output"),
            error_message=result.get("error_message"),
            duration_ms=duration,
        )


act_phase = ActPhase()
