"""
Planning Agent: task decomposition, workflow generation, and scheduling.
Uses LLM to break complex goals into structured action plans.
"""
from __future__ import annotations

import time
from typing import Any, ClassVar
from uuid import uuid4

from src.agents.base_agent import BaseAgent
from src.core.domain_objects import AgentType, ExecutionContext
from src.core.message_schemas import TaskDispatchPayload, TaskResultPayload
from src.llm.embeddings import get_llm_client
from src.memory.memory_service import memory_service

PLANNING_SYSTEM_PROMPT = """You are a Planning Agent in the COS-AA system.
Your job is to decompose complex goals into concrete, ordered action steps.

For each step, provide:
- step_number: sequential order
- description: what needs to be done
- tool_name: the tool to use (web_search, code_interpreter, file_io, database_query, or null if no tool needed)
- dependencies: list of step_numbers this step depends on
- is_critical: whether failure of this step should abort the whole plan

Respond in JSON with this schema:
{
  "plan_summary": "brief summary of the plan",
  "steps": [
    {
      "step_number": 1,
      "description": "...",
      "tool_name": "...",
      "dependencies": [],
      "is_critical": true
    }
  ]
}
"""


class PlanningAgent(BaseAgent):
    agent_type: ClassVar[AgentType] = AgentType.PLANNING
    supported_task_types: ClassVar[list[str]] = [
        "plan_generation",
        "task_decomposition",
        "workflow_scheduling",
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
            goal_description = task.input_data.get("goal", "")
            context_data = task.input_data.get("context", {})
            tenant_id = task.input_data.get(
                "tenant_id", str(task.session_id)
            )

            # Retrieve relevant procedural patterns from memory
            patterns = []
            try:
                patterns = await memory_service.procedural.find_best_pattern(
                    tenant_id=tenant_id,
                    task_type="plan_generation",
                    context_tags=[],
                )
            except Exception:
                pass

            user_prompt = f"""Goal: {goal_description}

Context: {context_data}

Previous successful patterns: {patterns if patterns else 'None available'}

Generate a detailed execution plan to achieve this goal."""

            llm_response = await self._llm.chat_completion_json(
                system_prompt=PLANNING_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,
            )

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


planning_agent = PlanningAgent()
