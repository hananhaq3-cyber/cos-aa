"""
Unit tests for the OODA engine state machine and cycle control.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from src.core.domain_objects import (
    CycleResult,
    ExecutionResult,
    GoalObject,
    OODAPhase,
    ObservationSet,
    SituationModel,
    ActionPlan,
)
from src.core.exceptions import OODATimeoutError, MaxIterationsExceededError
from src.hub.hub_state import CycleState


class TestCycleState:
    def test_default_creation(self):
        state = CycleState(
            tenant_id=uuid4(),
            session_id=uuid4(),
        )
        assert state.phase == OODAPhase.IDLE
        assert state.iteration == 0
        assert state.max_iterations == 5

    def test_to_dict_roundtrip(self):
        tenant_id = uuid4()
        session_id = uuid4()
        state = CycleState(
            tenant_id=tenant_id,
            session_id=session_id,
            max_iterations=3,
            goal_description="test goal",
        )
        d = state.to_dict()
        assert d["tenant_id"] == str(tenant_id)
        assert d["phase"] == "IDLE"
        assert d["max_iterations"] == 3

        restored = CycleState.from_dict(d)
        assert restored.tenant_id == tenant_id
        assert restored.phase == OODAPhase.IDLE


class TestOODAEngineUnit:
    """Tests for cycle logic — all external dependencies mocked."""

    @pytest.mark.asyncio
    async def test_single_iteration_goal_achieved(self):
        """When review says goal_achieved=True, cycle completes after one iteration."""
        from src.hub.ooda_engine import OODAEngine

        engine = OODAEngine()
        tenant_id = uuid4()
        session_id = uuid4()

        mock_observations = ObservationSet(observations=[])
        mock_situation = SituationModel(situation_summary="test")
        mock_plan = ActionPlan(goal_id=uuid4(), steps=[])
        mock_exec_result = ExecutionResult(
            plan_id=uuid4(), all_critical_succeeded=True
        )
        mock_cycle_result = CycleResult(
            cycle_number=1,
            goal_achieved=True,
            evidence="Goal achieved in test",
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
            mock_observe.execute = AsyncMock(return_value=mock_observations)
            mock_orient.execute = AsyncMock(return_value=mock_situation)
            mock_decide.execute = AsyncMock(return_value=mock_plan)
            mock_act.execute = AsyncMock(return_value=mock_exec_result)
            mock_review.execute = AsyncMock(return_value=mock_cycle_result)
            mock_pubsub.publish_ooda_progress = AsyncMock()

            result = await engine.run_cycle(
                tenant_id=tenant_id,
                session_id=session_id,
                user_message="test message",
                max_iterations=3,
            )

            assert result.goal_achieved is True
            assert result.evidence == "Goal achieved in test"
            assert mock_observe.execute.call_count == 1
            assert mock_review.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_max_iterations_returns_last_result(self):
        """When max iterations reached without goal, return last result."""
        from src.hub.ooda_engine import OODAEngine

        engine = OODAEngine()

        mock_cycle_result = CycleResult(
            cycle_number=1,
            goal_achieved=False,
            evidence="Still working",
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
            mock_review.execute = AsyncMock(return_value=mock_cycle_result)
            mock_pubsub.publish_ooda_progress = AsyncMock()

            result = await engine.run_cycle(
                tenant_id=uuid4(),
                session_id=uuid4(),
                user_message="test",
                max_iterations=2,
            )

            assert result.goal_achieved is False
            assert mock_review.execute.call_count == 2
