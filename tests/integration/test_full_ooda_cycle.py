"""
Integration test: Full OODA cycle execution with mocked LLM and external services.
"""
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from src.core.domain_objects import (
    ActionPlan,
    ActionStep,
    AgentType,
    CycleResult,
    ExecutionResult,
    ObservationSet,
    OODAPhase,
    SituationModel,
    StepResult,
)
from src.hub.ooda_engine import OODAEngine


@pytest.mark.asyncio
class TestFullOODACycle:
    async def test_complete_cycle_all_phases_execute(self):
        """
        Run a full OODA cycle: OBSERVE -> ORIENT -> DECIDE -> ACT -> REVIEW.
        Verify all 5 phases execute and state transitions happen correctly.
        """
        engine = OODAEngine()
        tenant_id = uuid4()
        session_id = uuid4()

        phase_transitions: list[str] = []

        async def track_transition(state, phase):
            phase_transitions.append(phase.value)
            state.phase = phase

        with (
            patch("src.hub.ooda_engine.hub_state_manager") as mock_hsm,
            patch("src.hub.ooda_engine.observe_phase") as mock_observe,
            patch("src.hub.ooda_engine.orient_phase") as mock_orient,
            patch("src.hub.ooda_engine.decide_phase") as mock_decide,
            patch("src.hub.ooda_engine.act_phase") as mock_act,
            patch("src.hub.ooda_engine.review_phase") as mock_review,
            patch("src.hub.ooda_engine.pubsub_manager") as mock_pubsub,
        ):
            mock_hsm.save = AsyncMock()
            mock_hsm.transition = AsyncMock(side_effect=track_transition)
            mock_hsm.delete = AsyncMock()
            mock_pubsub.publish_ooda_progress = AsyncMock()

            # OBSERVE returns observations
            mock_observe.execute = AsyncMock(
                return_value=ObservationSet(observations=[])
            )

            # ORIENT returns situation model
            mock_orient.execute = AsyncMock(
                return_value=SituationModel(
                    situation_summary="User wants AI exam help",
                    confidence=0.9,
                )
            )

            # DECIDE returns action plan
            plan_id = uuid4()
            step_id = uuid4()
            mock_decide.execute = AsyncMock(
                return_value=ActionPlan(
                    plan_id=plan_id,
                    goal_id=uuid4(),
                    steps=[
                        ActionStep(
                            step_id=step_id,
                            step_number=1,
                            agent_type=AgentType.KNOWLEDGE,
                            tool_name="web_search",
                            input_params={"query": "AI exam topics"},
                        )
                    ],
                )
            )

            # ACT returns execution result
            mock_act.execute = AsyncMock(
                return_value=ExecutionResult(
                    plan_id=plan_id,
                    step_results=[
                        StepResult(
                            step_id=step_id,
                            success=True,
                            output={"results": ["ML", "NLP"]},
                            duration_ms=800.0,
                        )
                    ],
                    all_critical_succeeded=True,
                    total_duration_ms=800.0,
                )
            )

            # REVIEW returns goal achieved
            mock_review.execute = AsyncMock(
                return_value=CycleResult(
                    cycle_number=1,
                    goal_achieved=True,
                    evidence="Study plan generated covering ML, NLP, and Neural Networks.",
                )
            )

            result = await engine.run_cycle(
                tenant_id=tenant_id,
                session_id=session_id,
                user_message="Help me prepare for my AI exam",
                max_iterations=3,
            )

            # Verify result
            assert result.goal_achieved is True
            assert "study plan" in result.evidence.lower() or "Study" in result.evidence

            # Verify all phase transitions occurred
            assert "OBSERVING" in phase_transitions
            assert "ORIENTING" in phase_transitions
            assert "DECIDING" in phase_transitions
            assert "ACTING" in phase_transitions
            assert "REVIEWING" in phase_transitions
            assert "COMPLETE" in phase_transitions

            # Verify each phase was called exactly once
            assert mock_observe.execute.call_count == 1
            assert mock_orient.execute.call_count == 1
            assert mock_decide.execute.call_count == 1
            assert mock_act.execute.call_count == 1
            assert mock_review.execute.call_count == 1

    async def test_cycle_loops_when_goal_not_achieved(self):
        """
        When review says goal_achieved=False, the engine loops back to OBSERVE.
        """
        engine = OODAEngine()
        call_count = 0

        async def review_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            return CycleResult(
                cycle_number=call_count,
                goal_achieved=call_count >= 2,  # Succeed on 2nd iteration
                evidence="Done" if call_count >= 2 else "Need more work",
                next_observations=ObservationSet(observations=[]),
            )

        with (
            patch("src.hub.ooda_engine.hub_state_manager") as mock_hsm,
            patch("src.hub.ooda_engine.observe_phase") as mock_observe,
            patch("src.hub.ooda_engine.orient_phase") as mock_orient,
            patch("src.hub.ooda_engine.decide_phase") as mock_decide,
            patch("src.hub.ooda_engine.act_phase") as mock_act,
            patch("src.hub.ooda_engine.review_phase") as mock_review,
            patch("src.hub.ooda_engine.pubsub_manager") as mock_pubsub,
        ):
            mock_hsm.save = AsyncMock()
            mock_hsm.transition = AsyncMock()
            mock_hsm.delete = AsyncMock()
            mock_pubsub.publish_ooda_progress = AsyncMock()
            mock_observe.execute = AsyncMock(
                return_value=ObservationSet(observations=[])
            )
            mock_orient.execute = AsyncMock(
                return_value=SituationModel(situation_summary="t")
            )
            mock_decide.execute = AsyncMock(
                return_value=ActionPlan(goal_id=uuid4())
            )
            mock_act.execute = AsyncMock(
                return_value=ExecutionResult(plan_id=uuid4())
            )
            mock_review.execute = AsyncMock(
                side_effect=review_side_effect
            )

            result = await engine.run_cycle(
                tenant_id=uuid4(),
                session_id=uuid4(),
                user_message="test",
                max_iterations=5,
            )

            assert result.goal_achieved is True
            assert mock_observe.execute.call_count == 2
            assert mock_review.execute.call_count == 2

    async def test_cycle_respects_tenant_isolation(self):
        """Verify that tenant_id is passed through all phases."""
        engine = OODAEngine()
        tenant_id = uuid4()
        session_id = uuid4()

        orient_tenant_ids: list = []

        async def orient_capture(**kwargs):
            orient_tenant_ids.append(kwargs.get("tenant_id"))
            return SituationModel(situation_summary="t")

        with (
            patch("src.hub.ooda_engine.hub_state_manager") as mock_hsm,
            patch("src.hub.ooda_engine.observe_phase") as mock_observe,
            patch("src.hub.ooda_engine.orient_phase") as mock_orient,
            patch("src.hub.ooda_engine.decide_phase") as mock_decide,
            patch("src.hub.ooda_engine.act_phase") as mock_act,
            patch("src.hub.ooda_engine.review_phase") as mock_review,
            patch("src.hub.ooda_engine.pubsub_manager") as mock_pubsub,
        ):
            mock_hsm.save = AsyncMock()
            mock_hsm.transition = AsyncMock()
            mock_hsm.delete = AsyncMock()
            mock_pubsub.publish_ooda_progress = AsyncMock()
            mock_observe.execute = AsyncMock(
                return_value=ObservationSet(observations=[])
            )
            mock_orient.execute = AsyncMock(side_effect=orient_capture)
            mock_decide.execute = AsyncMock(
                return_value=ActionPlan(goal_id=uuid4())
            )
            mock_act.execute = AsyncMock(
                return_value=ExecutionResult(plan_id=uuid4())
            )
            mock_review.execute = AsyncMock(
                return_value=CycleResult(goal_achieved=True, evidence="ok")
            )

            await engine.run_cycle(
                tenant_id=tenant_id,
                session_id=session_id,
                user_message="test",
            )

            assert orient_tenant_ids[0] == tenant_id
