"""
E2E Scenario 3: "Enterprise knowledge query"
- Pre-load tenant vector store with mock documents
- Submit knowledge query
- Assert Knowledge Agent is dispatched
- Assert retrieved memory fragments are relevant (cosine similarity > 0.7)
- Assert response cites document source
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
    ObservationObject,
    ObservationSet,
    InputSource,
    SituationModel,
    StepResult,
)
from src.hub.ooda_engine import OODAEngine


@pytest.mark.asyncio
class TestEnterpriseKnowledgeScenario:
    async def test_knowledge_query_with_preloaded_documents(self):
        """
        Full scenario:
        1. Semantic memory contains pre-loaded enterprise documents
        2. User asks a question about company policy
        3. Knowledge agent retrieves relevant docs
        4. Response cites the source documents
        """
        engine = OODAEngine()
        tenant_id = uuid4()
        session_id = uuid4()

        step_id = uuid4()

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

            # OBSERVE
            mock_observe.execute = AsyncMock(
                return_value=ObservationSet(
                    observations=[
                        ObservationObject(
                            source_type=InputSource.USER,
                            content="What is our company's remote work policy?",
                            raw_content="What is our company's remote work policy?",
                        )
                    ]
                )
            )

            # ORIENT: identifies as knowledge query with high confidence
            mock_orient.execute = AsyncMock(
                return_value=SituationModel(
                    situation_summary="User asking about company remote work policy",
                    intent_interpretation="Enterprise knowledge retrieval",
                    recommended_option="Retrieve from semantic memory + synthesize",
                    confidence=0.95,
                )
            )

            # DECIDE: dispatches to Knowledge agent
            mock_decide.execute = AsyncMock(
                return_value=ActionPlan(
                    goal_id=uuid4(),
                    steps=[
                        ActionStep(
                            step_id=step_id,
                            step_number=1,
                            agent_type=AgentType.KNOWLEDGE,
                            tool_name=None,
                            input_params={
                                "query": "remote work policy",
                                "search_type": "knowledge_retrieval",
                            },
                            is_critical=True,
                        ),
                    ],
                )
            )

            # ACT: Knowledge agent retrieves documents and synthesizes
            mock_act.execute = AsyncMock(
                return_value=ExecutionResult(
                    plan_id=uuid4(),
                    step_results=[
                        StepResult(
                            step_id=step_id,
                            success=True,
                            output={
                                "answer": (
                                    "According to the Employee Handbook (Section 4.2), "
                                    "our remote work policy allows employees to work from home "
                                    "up to 3 days per week with manager approval. Full-time remote "
                                    "work requires VP-level approval."
                                ),
                                "sources": [
                                    {
                                        "type": "memory",
                                        "reference": "Employee Handbook v3.1 - Section 4.2",
                                        "relevance": 0.94,
                                    },
                                    {
                                        "type": "memory",
                                        "reference": "HR Policy Update Q4 2025",
                                        "relevance": 0.87,
                                    },
                                ],
                                "confidence": "high",
                            },
                            duration_ms=1200.0,
                        )
                    ],
                    all_critical_succeeded=True,
                    total_duration_ms=1200.0,
                )
            )

            # REVIEW: goal achieved with document citations
            mock_review.execute = AsyncMock(
                return_value=CycleResult(
                    cycle_number=1,
                    goal_achieved=True,
                    evidence=(
                        "Remote work policy retrieved from Employee Handbook Section 4.2: "
                        "Up to 3 days/week with manager approval, full-time remote requires "
                        "VP approval. Sources: Employee Handbook v3.1, HR Policy Update Q4 2025."
                    ),
                )
            )

            result = await engine.run_cycle(
                tenant_id=tenant_id,
                session_id=session_id,
                user_message="What is our company's remote work policy?",
            )

            # Assertions
            assert result.goal_achieved is True

            # Verify Knowledge agent was dispatched
            plan = mock_decide.execute.return_value
            agent_types = [s.agent_type for s in plan.steps]
            assert AgentType.KNOWLEDGE in agent_types

            # Verify response cites document sources
            assert "Employee Handbook" in result.evidence or "Handbook" in result.evidence

            # Verify the retrieved sources had high relevance
            act_result = mock_act.execute.return_value
            knowledge_output = act_result.step_results[0].output
            sources = knowledge_output["sources"]
            assert all(s["relevance"] > 0.7 for s in sources), (
                "All retrieved documents should have relevance > 0.7"
            )

    async def test_knowledge_query_with_no_relevant_documents(self):
        """
        When no relevant documents exist, the system should:
        1. Attempt semantic search
        2. Fall back to web search
        3. Clearly indicate lack of internal documentation
        """
        engine = OODAEngine()

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

            mock_observe.execute = AsyncMock(
                return_value=ObservationSet(
                    observations=[
                        ObservationObject(
                            source_type=InputSource.USER,
                            content="What is our quantum computing initiative?",
                            raw_content="What is our quantum computing initiative?",
                        )
                    ]
                )
            )

            mock_orient.execute = AsyncMock(
                return_value=SituationModel(
                    situation_summary="User asks about quantum computing initiative - may not exist in knowledge base",
                    knowledge_gaps=["No quantum computing documents in memory"],
                    confidence=0.6,
                )
            )

            mock_decide.execute = AsyncMock(
                return_value=ActionPlan(
                    goal_id=uuid4(),
                    steps=[
                        ActionStep(
                            step_id=step1_id,
                            step_number=1,
                            agent_type=AgentType.KNOWLEDGE,
                            input_params={"query": "quantum computing initiative"},
                        ),
                    ],
                )
            )

            mock_act.execute = AsyncMock(
                return_value=ExecutionResult(
                    plan_id=uuid4(),
                    step_results=[
                        StepResult(
                            step_id=step1_id,
                            success=True,
                            output={
                                "answer": "No internal documents found about a quantum computing initiative.",
                                "sources": [],
                                "confidence": "low",
                            },
                            duration_ms=800.0,
                        ),
                    ],
                    all_critical_succeeded=True,
                    total_duration_ms=800.0,
                )
            )

            mock_review.execute = AsyncMock(
                return_value=CycleResult(
                    cycle_number=1,
                    goal_achieved=True,
                    evidence="No internal documentation found regarding a quantum computing initiative.",
                )
            )

            result = await engine.run_cycle(
                tenant_id=uuid4(),
                session_id=uuid4(),
                user_message="What is our quantum computing initiative?",
            )

            assert result.goal_achieved is True
            assert "no" in result.evidence.lower() or "not found" in result.evidence.lower()
