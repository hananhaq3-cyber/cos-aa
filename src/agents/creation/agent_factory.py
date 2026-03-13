"""
Agent Factory: capability gap detection, LLM-based agent definition
generation, and validation of auto-generated agent definitions.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from src.core.config import settings
from src.core.domain_objects import (
    AgentDefinition,
    AgentDefinitionStatus,
    CycleResult,
    FailureType,
    MemoryAccessSpec,
    ResourceLimits,
    ToolSpec,
    ValidationResult,
)
from src.agents.creation.agent_registry import agent_registry
from src.db.redis_client import redis_client, RedisClient
from src.llm.embeddings import get_llm_client
from src.tools.tool_registry import tool_registry

SPAWN_THRESHOLD = 3
SPAWN_WINDOW_SECONDS = 86400  # 24 hours

AGENT_DEFINITION_PROMPT = """You are a system architect for the COS-AA platform.
Given a capability gap description and sample failing tasks, generate a new AgentDefinition.

Requirements:
- The agent must have a clear, specific purpose
- Only reference tools from the available tool catalog
- The system prompt must instruct the agent on its specialized behavior
- Resource limits must be reasonable (max 10 concurrent tasks, max 16000 tokens)

Available tools in the catalog: {tool_catalog}

Respond in JSON matching this schema:
{{
  "agent_type_name": "string (UPPER_SNAKE_CASE)",
  "purpose": "string (1-2 sentences)",
  "trigger_conditions": ["when to activate this agent"],
  "tools": [
    {{"tool_name": "string", "tool_type": "string", "permissions_required": []}}
  ],
  "system_prompt": "string (the agent's instruction prompt)",
  "model_override": null,
  "resource_limits": {{
    "max_concurrent_tasks": 5,
    "max_llm_tokens_per_task": 8000,
    "max_tool_calls_per_task": 10,
    "timeout_seconds": 120
  }}
}}
"""


class AgentFactory:
    """Detects capability gaps and auto-generates new agent definitions."""

    async def check_for_capability_gap(
        self, tenant_id: UUID, cycle_result: CycleResult
    ) -> bool:
        """
        Called from the REVIEW phase. Checks if a CAPABILITY_MISSING failure
        should trigger an agent spawn request.
        Returns True if the spawn threshold has been reached.
        """
        if not cycle_result.failed_reason:
            return False
        if cycle_result.failed_reason.failure_type != FailureType.CAPABILITY_MISSING:
            return False

        task_type = cycle_result.failed_reason.task_type or "unknown"

        # Check if any existing agent can handle this
        existing = await agent_registry.list_types(tenant_id, status="ACTIVE")
        for agent_def in existing:
            if task_type.lower() in agent_def.purpose.lower():
                return False

        # Increment gap counter
        gap_key = RedisClient.gap_counter_key(tenant_id, task_type)
        count = await redis_client.client.incr(gap_key)
        if count == 1:
            await redis_client.client.expire(gap_key, SPAWN_WINDOW_SECONDS)

        return count >= SPAWN_THRESHOLD

    async def generate_definition(
        self,
        tenant_id: UUID,
        gap_description: str,
        sample_failures: list[dict[str, Any]] | None = None,
    ) -> AgentDefinition:
        """Use LLM to generate a new AgentDefinition from a capability gap."""
        llm = get_llm_client()

        available_tools = tool_registry.list_tools()

        user_prompt = f"""Capability gap detected:
{gap_description}

Sample failing tasks:
{sample_failures or 'None available'}

Generate a specialized agent definition to fill this gap."""

        system_prompt = AGENT_DEFINITION_PROMPT.format(
            tool_catalog=available_tools
        )

        response = await llm.chat_completion_json(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        content = response if isinstance(response, dict) else {}

        tools = [
            ToolSpec(
                tool_name=t.get("tool_name", ""),
                tool_type=t.get("tool_type", "CUSTOM"),
                permissions_required=t.get("permissions_required", []),
            )
            for t in content.get("tools", [])
        ]

        rl = content.get("resource_limits", {})
        resource_limits = ResourceLimits(
            max_concurrent_tasks=rl.get("max_concurrent_tasks", 5),
            max_llm_tokens_per_task=rl.get("max_llm_tokens_per_task", 8000),
            max_tool_calls_per_task=rl.get("max_tool_calls_per_task", 10),
            timeout_seconds=rl.get("timeout_seconds", 120),
        )

        definition = AgentDefinition(
            tenant_id=tenant_id,
            agent_type_name=content.get("agent_type_name", "AUTO_GENERATED"),
            purpose=content.get("purpose", gap_description),
            trigger_conditions=content.get("trigger_conditions", []),
            tools=tools,
            system_prompt=content.get("system_prompt", ""),
            model_override=content.get("model_override"),
            memory_access=MemoryAccessSpec(),
            resource_limits=resource_limits,
            created_by="SYSTEM_AUTO",
            status=AgentDefinitionStatus.DRAFT,
        )

        return definition

    def validate_definition(
        self, definition: AgentDefinition
    ) -> ValidationResult:
        """Validate an auto-generated agent definition."""
        errors: list[str] = []

        if not definition.agent_type_name:
            errors.append("agent_type_name is required")
        if not definition.purpose:
            errors.append("purpose is required")
        if not definition.system_prompt:
            errors.append("system_prompt is required")
        if len(definition.system_prompt) < 20:
            errors.append(
                "system_prompt too short (min 20 chars)"
            )

        # Validate tools exist in catalog
        for tool_spec in definition.tools:
            if not tool_registry.has_tool(tool_spec.tool_name):
                errors.append(
                    f"Tool '{tool_spec.tool_name}' not found in catalog"
                )

        # Validate resource limits
        rl = definition.resource_limits
        if rl.max_concurrent_tasks > 20:
            errors.append("max_concurrent_tasks exceeds limit of 20")
        if rl.max_llm_tokens_per_task > 32000:
            errors.append("max_llm_tokens_per_task exceeds limit of 32000")

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    async def submit_for_approval(
        self, definition: AgentDefinition, require_approval: bool = True
    ) -> AgentDefinition:
        """Submit a validated definition for human approval or auto-approve."""
        validation = self.validate_definition(definition)
        if not validation.valid:
            definition.status = AgentDefinitionStatus.REJECTED
            return definition

        if require_approval:
            definition.status = AgentDefinitionStatus.VALIDATING
        else:
            definition.status = AgentDefinitionStatus.ACTIVE

        await agent_registry.register_type(definition)
        return definition


agent_factory = AgentFactory()
