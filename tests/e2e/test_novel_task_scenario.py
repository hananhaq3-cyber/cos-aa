"""
E2E Scenario 2: "Novel task triggers agent spawn"
- Submit a task type no existing agent handles, 3 times within threshold window
- Assert SPAWN_AGENT_REQUEST emitted
- Assert AgentDefinition generated and passes validation
- Assert agent enters VALIDATING state
"""
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from src.core.domain_objects import (
    AgentDefinition,
    AgentDefinitionStatus,
    CycleResult,
    FailedReason,
    FailureType,
)
from src.agents.creation.agent_factory import AgentFactory


@pytest.mark.asyncio
class TestNovelTaskScenario:
    async def test_novel_task_triggers_spawn_after_threshold(self):
        """
        When the same capability gap occurs 3 times (SPAWN_THRESHOLD),
        the system should:
        1. Detect the gap pattern
        2. Generate a new AgentDefinition
        3. Validate it
        4. Submit for approval (status = VALIDATING)
        """
        factory = AgentFactory()
        tenant_id = uuid4()
        gap_counter = 0

        async def incr_side_effect(key):
            nonlocal gap_counter
            gap_counter += 1
            return gap_counter

        # Simulate 3 consecutive CAPABILITY_MISSING failures
        for iteration in range(3):
            result = CycleResult(
                goal_achieved=False,
                failed_reason=FailedReason(
                    failure_type=FailureType.CAPABILITY_MISSING,
                    message="No agent can handle cryptocurrency analysis",
                    task_type="crypto_analysis",
                ),
            )

            with (
                patch("src.agents.creation.agent_factory.agent_registry") as mock_reg,
                patch("src.agents.creation.agent_factory.redis_client") as mock_redis,
            ):
                mock_reg.list_types = AsyncMock(return_value=[])
                mock_redis.client.incr = AsyncMock(side_effect=incr_side_effect)
                mock_redis.client.expire = AsyncMock()

                gap_detected = await factory.check_for_capability_gap(
                    tenant_id, result
                )

                if iteration < 2:
                    assert gap_detected is False, f"Should not trigger on attempt {iteration + 1}"
                else:
                    assert gap_detected is True, "Should trigger on 3rd attempt"

    async def test_generated_definition_is_valid(self):
        """After gap detection, generate a definition and verify it's valid."""
        factory = AgentFactory()
        tenant_id = uuid4()

        mock_response = {
            "agent_type_name": "CRYPTO_ANALYST",
            "purpose": "Analyze cryptocurrency markets and provide trading insights",
            "trigger_conditions": ["crypto", "bitcoin", "trading", "market analysis"],
            "tools": [
                {"tool_name": "web_search", "tool_type": "WEB_SEARCH", "permissions_required": []}
            ],
            "system_prompt": (
                "You are a cryptocurrency analysis agent. Analyze market trends, "
                "evaluate token fundamentals, and provide data-driven trading insights. "
                "Always cite data sources and include confidence levels."
            ),
            "model_override": None,
            "resource_limits": {
                "max_concurrent_tasks": 5,
                "max_llm_tokens_per_task": 8000,
                "max_tool_calls_per_task": 10,
                "timeout_seconds": 120,
            },
        }

        with patch("src.agents.creation.agent_factory.get_llm_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.chat_completion_json = AsyncMock(return_value=mock_response)
            mock_get.return_value = mock_client

            with patch("src.agents.creation.agent_factory.tool_registry") as mock_tr:
                mock_tr.list_tools.return_value = ["web_search", "database_query"]
                mock_tr.has_tool = lambda name: name in ["web_search", "database_query"]

                definition = await factory.generate_definition(
                    tenant_id=tenant_id,
                    gap_description="Need agent for cryptocurrency market analysis",
                    sample_failures=[
                        {"task_id": str(uuid4()), "error": "CAPABILITY_MISSING"},
                    ],
                )

                # Verify definition structure
                assert definition.agent_type_name == "CRYPTO_ANALYST"
                assert definition.tenant_id == tenant_id
                assert len(definition.system_prompt) >= 20
                assert definition.status == AgentDefinitionStatus.DRAFT

                # Validate
                validation = factory.validate_definition(definition)
                assert validation.valid is True, f"Validation errors: {validation.errors}"

    async def test_submit_for_approval_sets_validating_status(self):
        """After validation, submit_for_approval should set status to VALIDATING."""
        factory = AgentFactory()
        tenant_id = uuid4()

        definition = AgentDefinition(
            tenant_id=tenant_id,
            agent_type_name="CRYPTO_ANALYST",
            purpose="Cryptocurrency market analysis",
            system_prompt="You are a crypto analyst agent with market analysis expertise and data-driven insights.",
            tools=[],
            status=AgentDefinitionStatus.DRAFT,
        )

        with (
            patch("src.agents.creation.agent_factory.tool_registry") as mock_tr,
            patch("src.agents.creation.agent_factory.agent_registry") as mock_reg,
        ):
            mock_tr.has_tool = lambda name: True
            mock_reg.register_type = AsyncMock(return_value=definition.definition_id)

            result = await factory.submit_for_approval(
                definition, require_approval=True
            )

            assert result.status == AgentDefinitionStatus.VALIDATING
            mock_reg.register_type.assert_called_once()

    async def test_auto_approve_sets_active_status(self):
        """With require_approval=False, definition goes directly to ACTIVE."""
        factory = AgentFactory()
        tenant_id = uuid4()

        definition = AgentDefinition(
            tenant_id=tenant_id,
            agent_type_name="AUTO_AGENT",
            purpose="Auto-approved agent for testing",
            system_prompt="You are an auto-approved agent for integration testing purposes.",
            tools=[],
            status=AgentDefinitionStatus.DRAFT,
        )

        with (
            patch("src.agents.creation.agent_factory.tool_registry") as mock_tr,
            patch("src.agents.creation.agent_factory.agent_registry") as mock_reg,
        ):
            mock_tr.has_tool = lambda name: True
            mock_reg.register_type = AsyncMock(return_value=definition.definition_id)

            result = await factory.submit_for_approval(
                definition, require_approval=False
            )

            assert result.status == AgentDefinitionStatus.ACTIVE
