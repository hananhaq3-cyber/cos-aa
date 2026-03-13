"""
ORIENT phase: retrieve memory, assemble context, run CoT reasoning.
"""
from uuid import UUID

from src.core.domain_objects import (
    CapabilityDescriptor,
    ContextBundle,
    CycleResult,
    GoalObject,
    ObservationSet,
    SituationModel,
)
from src.hub.cot_reasoner import cot_reasoner
from src.memory.memory_service import memory_service


class OrientPhase:
    """Retrieve context from memory and run CoT reasoning."""

    async def execute(
        self,
        tenant_id: UUID,
        session_id: UUID,
        observations: ObservationSet,
        goal: GoalObject,
        agent_capabilities: list[CapabilityDescriptor] | None = None,
        available_tools: list[str] | None = None,
        prior_outcomes: list[CycleResult] | None = None,
    ) -> SituationModel:
        query = " ".join(
            str(obs.content) for obs in observations.observations[:5]
        )

        memory_fragments = await memory_service.retrieve_context(
            tenant_id=tenant_id,
            query=query,
            session_id=session_id,
            top_k=5,
        )

        task_type_hint = self._infer_task_type(observations)
        pattern = await memory_service.find_pattern(tenant_id, task_type_hint)

        context = ContextBundle(
            current_observations=observations,
            relevant_memories=memory_fragments,
            active_goal=goal,
            agent_capabilities=agent_capabilities or [],
            available_tools=available_tools or [],
            constraints={
                "max_iterations": goal.max_iterations,
                "timeout_seconds": goal.timeout_seconds,
            },
            prior_cycle_outcomes=prior_outcomes or [],
        )

        if pattern:
            context.constraints["known_pattern"] = pattern["pattern_name"]
            context.constraints["pattern_success_rate"] = pattern[
                "success_count"
            ] / max(pattern["success_count"] + pattern["failure_count"], 1)

        return await cot_reasoner.reason(context)

    def _infer_task_type(self, observations: ObservationSet) -> str:
        if not observations.observations:
            return "unknown"
        first = str(observations.observations[0].content).lower()
        keywords = {
            "plan": "planning",
            "schedule": "planning",
            "organize": "planning",
            "learn": "learning",
            "study": "learning",
            "prepare": "learning",
            "monitor": "monitoring",
            "alert": "monitoring",
            "track": "monitoring",
            "search": "knowledge",
            "find": "knowledge",
            "look up": "knowledge",
            "research": "knowledge",
            "document": "knowledge",
        }
        for kw, tt in keywords.items():
            if kw in first:
                return tt
        return "general"


orient_phase = OrientPhase()
