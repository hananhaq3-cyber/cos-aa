"""
Mock LLM responses for testing — deterministic responses for each CoT phase.
"""
from src.llm.llm_client import LLMResponse


MOCK_COT_ORIENT_RESPONSE = LLMResponse(
    content={
        "cot_chain": [
            {
                "step_number": 1,
                "step_name": "Parse Intent",
                "reasoning": "User wants to prepare for an AI exam.",
                "confidence": 0.95,
            },
            {
                "step_number": 2,
                "step_name": "Identify Knowledge Gaps",
                "reasoning": "Need to identify key AI topics and create a study plan.",
                "confidence": 0.9,
            },
        ],
        "situation_summary": "User needs help preparing for an AI examination.",
        "intent_interpretation": "Academic preparation assistance",
        "knowledge_gaps": ["User's current knowledge level", "Exam format"],
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
        "confidence": 0.88,
        "requires_human_confirmation": False,
    },
    model="gpt-4o-test",
    prompt_tokens=500,
    completion_tokens=300,
    total_tokens=800,
)


MOCK_DECIDE_PLAN_RESPONSE = LLMResponse(
    content={
        "plan_summary": "Search for AI topics, then generate a study plan.",
        "steps": [
            {
                "step_number": 1,
                "description": "Search for key AI exam topics",
                "agent_type": "KNOWLEDGE",
                "tool_name": "web_search",
                "dependencies": [],
                "is_critical": True,
            },
            {
                "step_number": 2,
                "description": "Generate structured study plan",
                "agent_type": "PLANNING",
                "tool_name": None,
                "dependencies": [1],
                "is_critical": True,
            },
        ],
    },
    model="gpt-4o-test",
    prompt_tokens=400,
    completion_tokens=200,
    total_tokens=600,
)


MOCK_REVIEW_RESPONSE = LLMResponse(
    content={
        "goal_achieved": True,
        "evidence": "Study plan successfully generated with coverage of ML, NLP, and Neural Networks.",
        "confidence": 0.92,
        "suggestions_for_next_cycle": [],
    },
    model="gpt-4o-test",
    prompt_tokens=300,
    completion_tokens=150,
    total_tokens=450,
)


MOCK_SIMPLE_TEXT_RESPONSE = LLMResponse(
    content="This is a simple text response from the mock LLM.",
    model="gpt-4o-test",
    prompt_tokens=50,
    completion_tokens=20,
    total_tokens=70,
)
