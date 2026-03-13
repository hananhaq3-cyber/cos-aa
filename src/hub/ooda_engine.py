"""
The OODA Engine: main orchestrator that runs the Observe-Orient-Decide-Act-Review loop.
Includes HA leader election — only the leader HUB processes cycles.
"""
import logging
import time
from uuid import UUID, uuid4

from src.core.config import settings
from src.core.domain_objects import (
    CycleResult,
    GoalObject,
    OODAPhase,
    ObservationSet,
)
from src.core.exceptions import (
    HumanConfirmationRequired,
    MaxIterationsExceededError,
    OODATimeoutError,
)
from src.hub.hub_state import CycleState, hub_state_manager
from src.hub.leader_election import leader_election
from src.hub.observe import observe_phase
from src.hub.orient import orient_phase
from src.hub.decide import decide_phase
from src.hub.act import act_phase
from src.hub.review import review_phase
from src.messaging.pubsub import pubsub_manager

logger = logging.getLogger(__name__)


class OODAEngine:
    """
    Main OODA loop orchestrator.
    Manages the full lifecycle: IDLE -> OBSERVE -> ORIENT -> DECIDE -> ACT -> REVIEW -> (loop or COMPLETE).
    """

    async def run_cycle(
        self,
        tenant_id: UUID,
        session_id: UUID,
        user_message: str,
        goal_description: str | None = None,
        max_iterations: int | None = None,
        timeout_seconds: int | None = None,
    ) -> CycleResult:
        """
        Run a complete OODA cycle (potentially multiple iterations).
        Returns the final CycleResult.
        """
        # HA: attempt to acquire leadership before processing
        # In development mode, skip leader election (no Redis required)
        if settings.app_env != "development" and not leader_election.is_leader:
            try:
                acquired = await leader_election.try_acquire()
                if acquired:
                    leader_election.start_renewal()
                else:
                    logger.warning(
                        "Not the leader HUB — cannot process cycle for session %s",
                        session_id,
                    )
                    raise RuntimeError("This HUB instance is not the leader")
            except RuntimeError:
                raise
            except Exception as e:
                logger.warning("Leader election check failed: %s — proceeding anyway", e)

        max_iter = max_iterations or settings.default_max_ooda_iterations
        timeout = timeout_seconds or settings.default_ooda_cycle_timeout_seconds

        goal = GoalObject(
            description=goal_description or user_message,
            max_iterations=max_iter,
            timeout_seconds=timeout,
        )

        # Initialize cycle state
        state = CycleState(
            tenant_id=tenant_id,
            session_id=session_id,
            max_iterations=max_iter,
            goal_description=goal.description,
        )
        await hub_state_manager.save(state)

        agent_id = uuid4()  # HUB agent ID for this cycle
        start_time = time.perf_counter()
        current_observations: ObservationSet | None = None
        prior_outcomes: list[CycleResult] = []

        for iteration in range(1, max_iter + 1):
            # Timeout check
            elapsed = time.perf_counter() - start_time
            if elapsed > timeout:
                await hub_state_manager.transition(state, OODAPhase.FAILED)
                raise OODATimeoutError(str(state.cycle_id), state.phase.value)

            state.iteration = iteration

            # -- OBSERVE --
            await hub_state_manager.transition(state, OODAPhase.OBSERVING)
            await pubsub_manager.publish_ooda_progress(
                tenant_id, session_id, "OBSERVING"
            )

            observations = await observe_phase.execute(
                user_message=user_message if iteration == 1 else None,
                prior_observations=current_observations,
            )

            # -- ORIENT --
            await hub_state_manager.transition(state, OODAPhase.ORIENTING)
            await pubsub_manager.publish_ooda_progress(
                tenant_id, session_id, "ORIENTING"
            )

            situation = await orient_phase.execute(
                tenant_id=tenant_id,
                session_id=session_id,
                observations=observations,
                goal=goal,
                prior_outcomes=prior_outcomes,
            )

            # -- DECIDE --
            await hub_state_manager.transition(state, OODAPhase.DECIDING)
            await pubsub_manager.publish_ooda_progress(
                tenant_id, session_id, "DECIDING"
            )

            try:
                action_plan = await decide_phase.execute(
                    tenant_id=tenant_id,
                    goal=goal,
                    situation=situation,
                )
            except HumanConfirmationRequired as e:
                # Pause cycle: save state and notify user
                state.await_confirmation(e.action_plan)
                await hub_state_manager.save(state)
                await pubsub_manager.publish_ooda_progress(
                    tenant_id,
                    session_id,
                    "AWAITING_CONFIRMATION",
                    {"action_plan_summary": state.confirmation_action_plan},
                )
                return CycleResult(
                    cycle_id=state.cycle_id,
                    cycle_number=iteration,
                    goal_achieved=False,
                    evidence="Action plan requires human confirmation before execution.",
                )

            # -- ACT --
            await hub_state_manager.transition(state, OODAPhase.ACTING)
            await pubsub_manager.publish_ooda_progress(
                tenant_id, session_id, "ACTING"
            )

            execution_result = await act_phase.execute(
                tenant_id=tenant_id,
                session_id=session_id,
                plan=action_plan,
                trace_id=state.trace_id,
            )

            # -- REVIEW --
            await hub_state_manager.transition(state, OODAPhase.REVIEWING)
            await pubsub_manager.publish_ooda_progress(
                tenant_id, session_id, "REVIEWING"
            )

            cycle_result = await review_phase.execute(
                tenant_id=tenant_id,
                session_id=session_id,
                agent_id=agent_id,
                goal=goal,
                execution_result=execution_result,
                situation_model=situation,
                cycle_number=iteration,
            )

            prior_outcomes.append(cycle_result)

            # Check if goal achieved
            if cycle_result.goal_achieved:
                await hub_state_manager.transition(state, OODAPhase.COMPLETE)
                await pubsub_manager.publish_ooda_progress(
                    tenant_id,
                    session_id,
                    "COMPLETE",
                    {"evidence": cycle_result.evidence},
                )
                await hub_state_manager.delete(tenant_id, state.cycle_id)
                return cycle_result

            # Loop: carry forward observations
            current_observations = cycle_result.next_observations

        # Max iterations exceeded
        await hub_state_manager.transition(state, OODAPhase.FAILED)
        await hub_state_manager.delete(tenant_id, state.cycle_id)

        if prior_outcomes:
            return prior_outcomes[-1]

        raise MaxIterationsExceededError(str(state.cycle_id), max_iter)


ooda_engine = OODAEngine()
