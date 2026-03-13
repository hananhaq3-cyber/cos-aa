"""
OBSERVE phase: collect, classify, filter, and normalize all inputs.
"""
from src.core.domain_objects import (
    InputModality,
    InputSource,
    ObservationObject,
    ObservationSet,
)


class ObservePhase:
    """Collect and normalize all inputs into an ObservationSet."""

    async def execute(
        self,
        user_message: str | None = None,
        tool_results: list[dict] | None = None,
        agent_messages: list[dict] | None = None,
        prior_observations: ObservationSet | None = None,
    ) -> ObservationSet:
        observations: list[ObservationObject] = []

        if user_message:
            observations.append(ObservationObject(
                source_type=InputSource.USER,
                content=user_message,
                raw_content=user_message,
                modality=InputModality.TEXT,
                relevance_score=1.0,
            ))

        if tool_results:
            for tr in tool_results:
                observations.append(ObservationObject(
                    source_type=InputSource.TOOL,
                    content=tr.get("output", ""),
                    raw_content=str(tr),
                    modality=InputModality.JSON,
                    relevance_score=0.8,
                    metadata={"tool_name": tr.get("tool_name", "unknown")},
                ))

        if agent_messages:
            for am in agent_messages:
                observations.append(ObservationObject(
                    source_type=InputSource.AGENT,
                    content=am.get("content", ""),
                    raw_content=str(am),
                    modality=InputModality.JSON,
                    relevance_score=0.7,
                    metadata={"agent_type": am.get("agent_type", "unknown")},
                ))

        if prior_observations:
            for obs in prior_observations.observations:
                if obs.relevance_score > 0.5:
                    obs.relevance_score *= 0.8
                    observations.append(obs)

        observations.sort(key=lambda o: o.relevance_score, reverse=True)
        return ObservationSet(observations=observations)


observe_phase = ObservePhase()
