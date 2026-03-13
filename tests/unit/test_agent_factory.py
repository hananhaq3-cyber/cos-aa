"""
Unit tests for agent factory — capability gap detection and definition generation.
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
    MemoryAccessSpec,
    ResourceLimits,
    ToolSpec,
)
from src.agents.creation.agent_factory import AgentFactory


class TestCapabilityGapDetection:
    @pytest.mark.asyncio
    async def test_ignores_non_capability_failures(self):
        factory = AgentFactory()
        result = CycleResult(
            goal_achieved=False,
            failed_reason=FailedReason(
                failure_type=FailureType.RETRIABLE,
                message="Timeout",
            ),
        )

        with patch("src.agents.creation.agent_factory.redis_client") as mock_redis:
            gap = await factory.check_for_capability_gap(uuid4(), result)
            assert gap is False

    @pytest.mark.asyncio
    async def test_ignores_results_without_failure(self):
        factory = AgentFactory()
        result = CycleResult(goal_achieved=True, evidence="Done")

        gap = await factory.check_for_capability_gap(uuid4(), result)
        assert gap is False

    @pytest.mark.asyncio
    async def test_detects_gap_at_threshold(self):
        factory = AgentFactory()
        result = CycleResult(
            goal_achieved=False,
            failed_reason=FailedReason(
                failure_type=FailureType.CAPABILITY_MISSING,
                message="No handler",
                task_type="financial_analysis",
            ),
        )

        with (
            patch("src.agents.creation.agent_factory.agent_registry") as mock_reg,
            patch("src.agents.creation.agent_factory.redis_client") as mock_redis,
        ):
            mock_reg.list_types = AsyncMock(return_value=[])
            mock_redis.client.incr = AsyncMock(return_value=3)  # threshold
            mock_redis.client.expire = AsyncMock()

            gap = await factory.check_for_capability_gap(uuid4(), result)
            assert gap is True


class TestDefinitionValidation:
    def test_valid_definition_passes(self):
        factory = AgentFactory()
        defn = AgentDefinition(
            tenant_id=uuid4(),
            agent_type_name="FINANCIAL_ANALYST",
            purpose="Analyze financial reports",
            system_prompt="You are a financial analysis agent with expertise in reading reports.",
            tools=[],
            resource_limits=ResourceLimits(max_concurrent_tasks=5),
        )

        with patch("src.agents.creation.agent_factory.tool_registry") as mock_tr:
            mock_tr.has_tool = lambda name: True
            result = factory.validate_definition(defn)
            assert result.valid is True

    def test_empty_name_fails(self):
        factory = AgentFactory()
        defn = AgentDefinition(
            tenant_id=uuid4(),
            agent_type_name="",
            purpose="Test",
            system_prompt="A long enough system prompt for validation",
        )
        result = factory.validate_definition(defn)
        assert result.valid is False
        assert any("agent_type_name" in e for e in result.errors)

    def test_short_prompt_fails(self):
        factory = AgentFactory()
        defn = AgentDefinition(
            tenant_id=uuid4(),
            agent_type_name="TEST",
            purpose="Test",
            system_prompt="Too short",
        )
        result = factory.validate_definition(defn)
        assert result.valid is False
        assert any("system_prompt" in e for e in result.errors)

    def test_excessive_resources_fails(self):
        factory = AgentFactory()
        defn = AgentDefinition(
            tenant_id=uuid4(),
            agent_type_name="TEST",
            purpose="Test",
            system_prompt="A long enough system prompt for validation testing.",
            resource_limits=ResourceLimits(max_concurrent_tasks=100),
        )
        result = factory.validate_definition(defn)
        assert result.valid is False
        assert any("max_concurrent_tasks" in e for e in result.errors)

    def test_unknown_tool_fails(self):
        factory = AgentFactory()
        defn = AgentDefinition(
            tenant_id=uuid4(),
            agent_type_name="TEST",
            purpose="Test",
            system_prompt="A long enough system prompt for validation testing.",
            tools=[ToolSpec(tool_name="nonexistent_tool", tool_type="CUSTOM")],
        )

        with patch("src.agents.creation.agent_factory.tool_registry") as mock_tr:
            mock_tr.has_tool = lambda name: False
            result = factory.validate_definition(defn)
            assert result.valid is False
            assert any("nonexistent_tool" in e for e in result.errors)
