"""
DECIDE phase: generate an action plan from the SituationModel.
Raises HumanConfirmationRequired when the situation model flags human oversight.
"""
from uuid import UUID

from src.core.domain_objects import (
    ActionPlan,
    ActionStep,
    AgentType,
    GoalObject,
    SituationModel,
)
from src.core.exceptions import HumanConfirmationRequired


class DecidePhase:
    """Generate and validate an action plan from the ORIENT output."""

    async def execute(
        self,
        tenant_id: UUID,
        goal: GoalObject,
        situation: SituationModel,
    ) -> ActionPlan:
        steps = await self._generate_steps(situation)
        plan = ActionPlan(goal_id=goal.goal_id, steps=steps)

        if situation.requires_human_confirmation:
            raise HumanConfirmationRequired(plan)

        return plan

    async def _generate_steps(
        self, situation: SituationModel
    ) -> list[ActionStep]:
        steps: list[ActionStep] = []

        option = None
        for opt in situation.options:
            if opt.name == situation.recommended_option:
                option = opt
                break
        if option is None and situation.options:
            option = situation.options[0]

        if option is None:
            steps.append(ActionStep(
                step_number=1,
                agent_type=AgentType.KNOWLEDGE,
                input_params={"query": situation.situation_summary},
                timeout_seconds=60,
            ))
            return steps

        approach_text = option.approach.lower()
        step_num = 0

        if any(
            kw in approach_text
            for kw in ["search", "retrieve", "find", "look up", "research"]
        ):
            step_num += 1
            steps.append(ActionStep(
                step_number=step_num,
                agent_type=AgentType.KNOWLEDGE,
                input_params={
                    "query": situation.situation_summary,
                    "approach": option.approach,
                },
                timeout_seconds=60,
            ))

        if any(
            kw in approach_text
            for kw in ["plan", "schedule", "organize", "structure", "outline"]
        ):
            step_num += 1
            steps.append(ActionStep(
                step_number=step_num,
                agent_type=AgentType.PLANNING,
                input_params={
                    "goal": situation.situation_summary,
                    "approach": option.approach,
                },
                timeout_seconds=90,
                depends_on=[
                    s.step_id
                    for s in steps
                    if s.agent_type == AgentType.KNOWLEDGE
                ],
            ))

        if any(
            kw in approach_text
            for kw in ["learn", "adapt", "personalize", "preference"]
        ):
            step_num += 1
            steps.append(ActionStep(
                step_number=step_num,
                agent_type=AgentType.LEARNING,
                input_params={"context": situation.situation_summary},
                timeout_seconds=60,
            ))

        if any(
            kw in approach_text
            for kw in ["monitor", "track", "deadline", "alert"]
        ):
            step_num += 1
            steps.append(ActionStep(
                step_number=step_num,
                agent_type=AgentType.MONITORING,
                input_params={"target": situation.situation_summary},
                timeout_seconds=30,
            ))

        if not steps:
            steps.append(ActionStep(
                step_number=1,
                agent_type=AgentType.KNOWLEDGE,
                input_params={"query": situation.situation_summary},
                timeout_seconds=60,
            ))

        return steps


decide_phase = DecidePhase()
