"""
Unit tests for CoT reasoner prompt construction and response parsing.
"""
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from src.core.domain_objects import (
    ContextBundle,
    GoalObject,
    ObservationSet,
    ObservationObject,
    InputSource,
    MemoryFragment,
    MemoryTier,
)
from src.hub.cot_reasoner import build_cot_user_prompt, CoTReasoner


class TestBuildCoTUserPrompt:
    def test_prompt_contains_goal(self):
        goal = GoalObject(description="Help with AI exam")
        context = ContextBundle(
            current_observations=ObservationSet(observations=[]),
            active_goal=goal,
        )
        prompt = build_cot_user_prompt(context)
        assert "Help with AI exam" in prompt

    def test_prompt_contains_observations(self):
        obs = ObservationObject(
            source_type=InputSource.USER,
            content="I need help studying",
            raw_content="I need help studying",
        )
        context = ContextBundle(
            current_observations=ObservationSet(observations=[obs]),
            active_goal=GoalObject(description="study"),
        )
        prompt = build_cot_user_prompt(context)
        assert "I need help studying" in prompt

    def test_prompt_contains_memories(self):
        mem = MemoryFragment(
            tier=MemoryTier.SEMANTIC,
            content="Previous study session notes",
            summary="Previous study session notes",
            relevance_score=0.8,
        )
        context = ContextBundle(
            current_observations=ObservationSet(observations=[]),
            active_goal=GoalObject(description="study"),
            relevant_memories=[mem],
        )
        prompt = build_cot_user_prompt(context)
        assert "Previous study session notes" in prompt


class TestCoTReasoner:
    @pytest.mark.asyncio
    async def test_reason_returns_situation_model(self):
        reasoner = CoTReasoner()
        context = ContextBundle(
            current_observations=ObservationSet(observations=[]),
            active_goal=GoalObject(description="test goal"),
        )

        # chat_completion_json returns a dict, not LLMResponse
        mock_json_response = {
            "situation_summary": "User needs help preparing for an AI examination.",
            "intent_interpretation": "Academic preparation assistance",
            "knowledge_gaps": ["User's current knowledge level", "Exam format"],
            "reasoning_steps": [
                "User wants to prepare for an AI exam.",
                "Need to identify key AI topics and create a study plan.",
            ],
            "options": [
                {
                    "name": "Comprehensive Study Plan",
                    "approach": "Generate a structured study plan covering all major AI topics.",
                    "pros": ["Thorough coverage", "Organized"],
                    "cons": ["May be overwhelming"],
                    "risk_level": "low",
                }
            ],
            "recommended_option": "Comprehensive Study Plan",
            "reasoning_confidence": 0.88,
            "requires_human_confirmation": False,
        }

        with patch("src.hub.cot_reasoner.get_llm_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.chat_completion_json = AsyncMock(
                return_value=mock_json_response
            )
            mock_get.return_value = mock_client

            situation = await reasoner.reason(context)

            assert situation.situation_summary is not None
            assert situation.confidence > 0
            assert len(situation.cot_chain) > 0
