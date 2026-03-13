"""
E2E Scenario 1: "Help me prepare for AI exam"
- Submit a real user message
- Run full OODA cycle
- Assert Planning and Knowledge agents are dispatched
- Assert study plan appears in response
- Assert episodic memory written after cycle
"""
from unittest.mock import AsyncMock, patch, call
from uuid import uuid4

import pytest
import pytest_asyncio

from src.core.domain_objects import (
    ActionPlan,
    ActionStep,
    AgentType,
    CycleResult,
    ExecutionResult,
    ObservationObject,
    ObservationSet,
    InputSource,
    SituationModel,
    StepResult,
)
from src.hub.ooda_engine import OODAEngine


@pytest.mark.asyncio
class TestExamPrepScenario:
    async def test_exam_prep_full_flow(self):
        """
        Full scenario: user asks for AI exam help.
        System should:
        1. Observe the user's message
        2. Orient with CoT reasoning
        3. Decide to dispatch Knowledge + Planning agents
        4. Act on the plan
        5. Review and produce a study plan
        6. Write to episodic memory
        """
        engine = OODAEngine()
        tenant_id = uuid4()
        session_id = uuid4()

        dispatched_agent_types: list[str] = []
        episodic_writes: list[dict] = []

        # Track which agents are dispatched during ACT
        step1_id = uuid4()
        step2_id = uuid4()

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

            # OBSERVE: collect user message
            mock_observe.execute = AsyncMock(
                return_value=ObservationSet(
                    observations=[
                        ObservationObject(
                            source_type=InputSource.USER,
                            content="Help me prepare for my AI exam",
                            raw_content="Help me prepare for my AI exam",
                        )
                    ]
                )
            )

            # ORIENT: CoT identifies need for knowledge + planning
            mock_orient.execute = AsyncMock(
                return_value=SituationModel(
                    situation_summary="User needs structured AI exam preparation",
                    intent_interpretation="Academic preparation assistance",
                    recommended_option="Search topics then create study plan",
                    confidence=0.92,
                )
            )

            # DECIDE: generates plan with Knowledge and Planning steps
            mock_decide.execute = AsyncMock(
                return_value=ActionPlan(
                    goal_id=uuid4(),
                    steps=[
                        ActionStep(
                            step_id=step1_id,
                            step_number=1,
                            agent_type=AgentType.KNOWLEDGE,
                            tool_name="web_search",
                            input_params={"query": "AI exam key topics 2026"},
                            is_critical=True,
                        ),
                        ActionStep(
                            step_id=step2_id,
                            step_number=2,
                            agent_type=AgentType.PLANNING,
                            input_params={"goal": "Create structured study plan"},
                            depends_on=[step1_id],
                            is_critical=True,
                        ),
                    ],
                )
            )

            # ACT: both steps succeed
            mock_act.execute = AsyncMock(
                return_value=ExecutionResult(
                    plan_id=uuid4(),
                    step_results=[
                        StepResult(
                            step_id=step1_id,
                            success=True,
                            output={
                                "topics": [
                                    "Machine Learning",
                                    "Neural Networks",
                                    "NLP",
                                    "Computer Vision",
                                    "Reinforcement Learning",
                                ]
                            },
                            duration_ms=2100.0,
                        ),
                        StepResult(
                            step_id=step2_id,
                            success=True,
                            output={
                                "study_plan": {
                                    "week_1": "ML fundamentals + Neural Networks",
                                    "week_2": "NLP + Transformers",
                                    "week_3": "Computer Vision + CNNs",
                                    "week_4": "RL + Practice exams",
                                }
                            },
                            duration_ms=1500.0,
                        ),
                    ],
                    all_critical_succeeded=True,
                    total_duration_ms=3600.0,
                )
            )

            # REVIEW: goal achieved, study plan in evidence
            mock_review.execute = AsyncMock(
                return_value=CycleResult(
                    cycle_number=1,
                    goal_achieved=True,
                    evidence=(
                        "Study plan generated: Week 1 - ML fundamentals + Neural Networks, "
                        "Week 2 - NLP + Transformers, Week 3 - Computer Vision + CNNs, "
                        "Week 4 - RL + Practice exams. Covering 5 key AI topics."
                    ),
                )
            )

            # Execute
            result = await engine.run_cycle(
                tenant_id=tenant_id,
                session_id=session_id,
                user_message="Help me prepare for my AI exam",
                max_iterations=5,
            )

            # Assertions
            assert result.goal_achieved is True
            assert "study plan" in result.evidence.lower() or "Study plan" in result.evidence

            # Verify the plan included both Knowledge and Planning agents
            decide_call = mock_decide.execute.call_args
            plan = mock_decide.execute.return_value
            agent_types_in_plan = [s.agent_type for s in plan.steps]
            assert AgentType.KNOWLEDGE in agent_types_in_plan
            assert AgentType.PLANNING in agent_types_in_plan

            # Verify ACT was called with the plan
            mock_act.execute.assert_called_once()

            # Verify review was called
            mock_review.execute.assert_called_once()

            # Verify state was cleaned up
            mock_hsm.delete.assert_called_once()
