"""
Chain-of-Thought reasoning module.
Builds structured prompts, calls LLM, parses JSON responses.
"""
from typing import Any

from src.core.config import settings
from src.core.domain_objects import (
    ContextBundle,
    CoTOption,
    CoTStep,
    RiskLevel,
    SituationModel,
)
from src.core.exceptions import CoTParsingError
from src.llm.embeddings import get_llm_client

COT_SYSTEM_PROMPT = """You are the reasoning core of a cognitive AI operating system called COS-AA.
Your role is to analyze situations step by step before reaching any conclusion.

You MUST output valid JSON conforming to this exact schema:
{
  "situation_summary": "string",
  "intent_interpretation": "string",
  "knowledge_gaps": ["string"],
  "options": [
    {
      "name": "string",
      "approach": "string",
      "pros": ["string"],
      "cons": ["string"],
      "risk_level": "low|medium|high"
    }
  ],
  "recommended_option": "string (must match one option name)",
  "reasoning_confidence": 0.0-1.0,
  "requires_human_confirmation": true|false
}"""


def build_cot_user_prompt(context: ContextBundle) -> str:
    observations_text = "\n".join(
        f"- [{obs.source_type.value}] {obs.content}"
        for obs in context.current_observations.observations
    ) or "No observations"

    memory_text = "\n".join(
        f"- [{mem.tier.value}] (relevance: {mem.relevance_score:.2f}) {mem.summary}"
        for mem in context.relevant_memories
    ) or "No relevant memories"

    capabilities_text = "\n".join(
        f"- {cap.task_type} (tools: {', '.join(cap.required_tool_names)})"
        for cap in context.agent_capabilities
    ) or "No agents available"

    tools_text = ", ".join(context.available_tools) or "No tools available"

    constraints_text = "\n".join(
        f"- {k}: {v}" for k, v in context.constraints.items()
    ) or "No constraints"

    prior_text = ""
    if context.prior_cycle_outcomes:
        prior_text = "\n## Prior Cycle Outcomes\n" + "\n".join(
            f"- Cycle {cr.cycle_number}: {'Achieved' if cr.goal_achieved else 'Not achieved'} — {cr.evidence}"
            for cr in context.prior_cycle_outcomes
        )

    return f"""## Current Observations
{observations_text}

## Relevant Past Experience
{memory_text}

## Active Goal
{context.active_goal.description}
Success criteria: {', '.join(context.active_goal.success_criteria) or 'Not specified'}

## Available Agents
{capabilities_text}

## Available Tools
{tools_text}

## Constraints
{constraints_text}
{prior_text}

Reason through this step by step:
Step 1 - Situation Analysis: What is currently happening? What is the user's true intent?
Step 2 - Gap Analysis: What do I know? What am I missing?
Step 3 - Option Generation: What are 2-3 possible approaches and trade-offs?
Step 4 - Risk Assessment: What could go wrong with each option?
Step 5 - Recommendation: Which approach is best given constraints? Why?"""


class CoTReasoner:
    """Performs Chain-of-Thought reasoning via LLM."""

    async def reason(self, context: ContextBundle) -> SituationModel:
        llm = get_llm_client()

        messages = [
            {"role": "system", "content": COT_SYSTEM_PROMPT},
            {"role": "user", "content": build_cot_user_prompt(context)},
        ]

        result = await llm.chat_completion_json(
            messages=messages, temperature=0.3
        )
        model = self._parse_result(result)

        if model.confidence < settings.cot_confidence_threshold:
            messages.append({"role": "assistant", "content": str(result)})
            messages.append({
                "role": "user",
                "content": (
                    "Your confidence was low. Please reconsider with more careful analysis. "
                    "Are there approaches you missed? Can you be more specific about the recommended option?"
                ),
            })
            result = await llm.chat_completion_json(
                messages=messages, temperature=0.2
            )
            model = self._parse_result(result)

            if model.confidence < settings.cot_confidence_threshold:
                model.requires_human_confirmation = True

        return model

    def _parse_result(self, data: dict[str, Any]) -> SituationModel:
        try:
            options = []
            for opt in data.get("options", []):
                options.append(CoTOption(
                    name=opt.get("name", ""),
                    approach=opt.get("approach", ""),
                    pros=opt.get("pros", []),
                    cons=opt.get("cons", []),
                    risk_level=RiskLevel(opt.get("risk_level", "medium")),
                ))

            return SituationModel(
                cot_chain=[
                    CoTStep(
                        step_number=i + 1,
                        step_name=f"Step {i + 1}",
                        reasoning=str(r),
                    )
                    for i, r in enumerate(data.get("reasoning_steps", []))
                ],
                situation_summary=data.get("situation_summary", ""),
                intent_interpretation=data.get("intent_interpretation", ""),
                knowledge_gaps=data.get("knowledge_gaps", []),
                options=options,
                recommended_option=data.get("recommended_option", ""),
                confidence=float(data.get("reasoning_confidence", 0.5)),
                requires_human_confirmation=data.get(
                    "requires_human_confirmation", False
                ),
            )
        except (KeyError, ValueError, TypeError) as e:
            raise CoTParsingError(f"Failed to parse CoT response: {e}")


cot_reasoner = CoTReasoner()
