"""
REVIEW phase: evaluate goal success, write to memory, trigger adaptation signals.
"""
from uuid import UUID

from src.core.domain_objects import (
    CycleResult,
    ExecutionResult,
    FailedReason,
    FailureType,
    GoalObject,
    ObservationSet,
    SituationModel,
)
from src.memory.memory_service import memory_service


class ReviewPhase:
    """Evaluate OODA cycle outcome and determine next action."""

    async def execute(
        self,
        tenant_id: UUID,
        session_id: UUID,
        agent_id: UUID,
        goal: GoalObject,
        execution_result: ExecutionResult,
        situation_model: SituationModel,
        cycle_number: int,
    ) -> CycleResult:
        goal_achieved = self._evaluate_success(goal, execution_result)

        failed_reason = None
        if not goal_achieved and not execution_result.all_critical_succeeded:
            failed_steps = [
                sr
                for sr in execution_result.step_results
                if not sr.success
            ]
            if failed_steps:
                failed_reason = FailedReason(
                    failure_type=FailureType.RETRIABLE,
                    message=failed_steps[0].error_message
                    or "Step execution failed",
                )

        successful_outputs = [
            str(sr.output)
            for sr in execution_result.step_results
            if sr.success and sr.output
        ]
        evidence = (
            " | ".join(successful_outputs)
            if successful_outputs
            else "No successful outputs"
        )

        await memory_service.write_episodic(
            tenant_id=tenant_id,
            session_id=session_id,
            agent_id=agent_id,
            event_type="TASK_COMPLETE" if goal_achieved else "TASK_INCOMPLETE",
            content={
                "goal": goal.description,
                "achieved": goal_achieved,
                "evidence": evidence,
                "cycle_number": cycle_number,
                "situation_summary": situation_model.situation_summary,
                "recommended_option": situation_model.recommended_option,
                "step_count": len(execution_result.step_results),
                "duration_ms": execution_result.total_duration_ms,
            },
            importance_score=0.8 if goal_achieved else 0.6,
        )

        next_observations = None
        if not goal_achieved:
            from src.hub.observe import observe_phase

            next_observations = await observe_phase.execute(
                tool_results=[
                    {"output": sr.output, "tool_name": str(sr.step_id)}
                    for sr in execution_result.step_results
                    if sr.output
                ],
            )

        return CycleResult(
            cycle_number=cycle_number,
            goal_achieved=goal_achieved,
            evidence=evidence,
            failed_reason=failed_reason,
            next_observations=next_observations,
            execution_result=execution_result,
        )

    def _evaluate_success(
        self, goal: GoalObject, execution: ExecutionResult
    ) -> bool:
        if not execution.all_critical_succeeded:
            return False
        return True


review_phase = ReviewPhase()
