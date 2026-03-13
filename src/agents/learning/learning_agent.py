"""
Learning Agent: tracks user preferences, adapts behavior, and identifies
optimization opportunities from episodic memory analysis.
"""
from __future__ import annotations

import time
from typing import Any, ClassVar
from uuid import UUID

from src.agents.base_agent import BaseAgent
from src.core.domain_objects import AgentType
from src.core.message_schemas import TaskDispatchPayload, TaskResultPayload
from src.llm.embeddings import get_llm_client
from src.memory.memory_service import memory_service

LEARNING_SYSTEM_PROMPT = """You are a Learning Agent in the COS-AA system.
Your job is to analyze past task outcomes and user interactions to:
1. Identify patterns of success and failure
2. Extract user preferences and working style
3. Suggest optimizations for future task execution
4. Update procedural memory with successful strategies

Respond in JSON with this schema:
{
  "insights": [
    {
      "type": "preference|pattern|optimization|warning",
      "description": "...",
      "confidence": 0.0-1.0,
      "actionable": true/false,
      "suggested_action": "..."
    }
  ],
  "preference_updates": [
    {
      "key": "...",
      "value": "...",
      "reason": "..."
    }
  ],
  "procedural_patterns": [
    {
      "task_type": "...",
      "strategy": "...",
      "success_indicators": ["..."]
    }
  ]
}
"""


class LearningAgent(BaseAgent):
    agent_type: ClassVar[AgentType] = AgentType.LEARNING
    supported_task_types: ClassVar[list[str]] = [
        "behavior_analysis",
        "preference_extraction",
        "strategy_optimization",
        "pattern_learning",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._llm = get_llm_client()

    async def execute_task(
        self, task: TaskDispatchPayload
    ) -> TaskResultPayload:
        start = time.perf_counter()
        self._current_task_count += 1

        try:
            analysis_type = task.input_data.get("analysis_type", "general")
            session_id = task.session_id
            tenant_id = task.input_data.get("tenant_id", str(session_id))

            # Retrieve recent episodic memories for analysis
            recent_episodes = []
            try:
                recent_episodes = await memory_service.episodic.query_recent(
                    tenant_id=tenant_id,
                    session_id=str(session_id),
                    limit=20,
                )
            except Exception:
                pass

            episode_summaries = []
            for ep in recent_episodes:
                episode_summaries.append(
                    {
                        "event_type": ep.get("event_type", ""),
                        "content": ep.get("content", {}),
                        "importance": ep.get("importance_score", 0.0),
                    }
                )

            user_prompt = f"""Analysis type: {analysis_type}

Recent task episodes ({len(episode_summaries)} entries):
{episode_summaries}

Additional context: {task.input_data.get('context', {})}

Analyze these episodes and extract insights, preference updates, and procedural patterns."""

            llm_response = await self._llm.chat_completion_json(
                system_prompt=LEARNING_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.4,
            )

            # Store learned patterns back to procedural memory
            if isinstance(llm_response.content, dict):
                patterns = llm_response.content.get("procedural_patterns", [])
                for pattern in patterns:
                    try:
                        await memory_service.procedural.store_pattern(
                            tenant_id=tenant_id,
                            task_type=pattern.get("task_type", "general"),
                            strategy_description=pattern.get("strategy", ""),
                            context_tags=pattern.get(
                                "success_indicators", []
                            ),
                        )
                    except Exception:
                        pass

            elapsed = (time.perf_counter() - start) * 1000
            return TaskResultPayload(
                task_id=task.task_id,
                success=True,
                output=llm_response.content,
                duration_ms=elapsed,
                tokens_consumed=llm_response.usage.get("total_tokens", 0),
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


learning_agent = LearningAgent()
