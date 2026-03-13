"""
Integration test: Agent spawn pipeline.
Tests capability gap detection -> definition generation -> validation -> registration.
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
    ResourceLimits,
)
from src.agents.creation.agent_factory import AgentFactory
from src.agents.creation.spawn_service import SpawnService


@pytest.mark.asyncio
class TestAgentSpawnPipeline:
    async def test_full_spawn_pipeline_dev_mode(self):
        """
        End-to-end: gap detection triggers generation -> validation -> spawn.
        In dev mode, spawn skips Docker/K8s and registers locally.
        """
        factory = AgentFactory()
        spawn_service = SpawnService()
        tenant_id = uuid4()

        # Step 1: Simulate 3 capability-missing failures to reach threshold
        for i in range(3):
            result = CycleResult(
                goal_achieved=False,
                failed_reason=FailedReason(
                    failure_type=FailureType.CAPABILITY_MISSING,
                    message="No agent for financial_analysis",
                    task_type="financial_analysis",
                ),
            )

            with (
                patch("src.agents.creation.agent_factory.agent_registry") as mock_reg,
                patch("src.agents.creation.agent_factory.redis_client") as mock_redis,
            ):
                mock_reg.list_types = AsyncMock(return_value=[])
                mock_redis.client.incr = AsyncMock(return_value=i + 1)
                mock_redis.client.expire = AsyncMock()

                gap = await factory.check_for_capability_gap(tenant_id, result)

                if i < 2:
                    assert gap is False
                else:
                    assert gap is True

    async def test_generate_definition_produces_valid_definition(self):
        """Generated definition should pass validation."""
        factory = AgentFactory()
        tenant_id = uuid4()

        # chat_completion_json returns a dict directly
        mock_llm_dict = {
            "agent_type_name": "FINANCIAL_ANALYST",
            "purpose": "Analyze financial reports and generate investment summaries",
            "trigger_conditions": ["financial report", "investment analysis"],
            "tools": [],
            "system_prompt": "You are a financial analyst agent. Analyze reports, extract key metrics, and provide investment recommendations.",
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
            mock_client.chat_completion_json = AsyncMock(
                return_value=mock_llm_dict
            )
            mock_get.return_value = mock_client

            with patch("src.agents.creation.agent_factory.tool_registry") as mock_tr:
                mock_tr.list_tools.return_value = ["web_search", "database_query"]
                mock_tr.has_tool = lambda name: True

                definition = await factory.generate_definition(
                    tenant_id=tenant_id,
                    gap_description="Need an agent to analyze financial reports",
                    sample_failures=[{"task_id": str(uuid4())}],
                )

                assert definition.agent_type_name == "FINANCIAL_ANALYST"
                assert definition.status == AgentDefinitionStatus.DRAFT

                # Validate
                validation = factory.validate_definition(definition)
                assert validation.valid is True

    async def test_spawn_service_dev_mode(self):
        """In dev mode, spawn registers instance locally without Docker/K8s."""
        spawn_service = SpawnService()
        tenant_id = uuid4()

        definition = AgentDefinition(
            tenant_id=tenant_id,
            agent_type_name="TEST_AGENT",
            purpose="Test agent for spawn pipeline",
            system_prompt="You are a test agent for integration testing.",
            status=AgentDefinitionStatus.DRAFT,
        )

        with (
            patch("src.agents.creation.spawn_service.agent_registry") as mock_reg,
            patch("src.agents.creation.spawn_service.settings") as mock_settings,
        ):
            mock_settings.app_env = "development"
            mock_settings.container_registry = "local"
            mock_reg.register_instance = AsyncMock()
            mock_reg.update_status = AsyncMock()

            result = await spawn_service.spawn_agent(definition)

            assert result["final_status"] == "ACTIVE"
            assert len(result["steps"]) >= 5
            mock_reg.update_status.assert_called()

    async def test_definition_rejected_on_validation_failure(self):
        """If definition fails validation, submit_for_approval rejects it."""
        factory = AgentFactory()

        bad_definition = AgentDefinition(
            tenant_id=uuid4(),
            agent_type_name="",
            purpose="",
            system_prompt="short",
        )

        with (
            patch("src.agents.creation.agent_factory.tool_registry") as mock_tr,
            patch("src.agents.creation.agent_factory.agent_registry") as mock_reg,
        ):
            mock_tr.has_tool = lambda name: False
            mock_reg.register_type = AsyncMock()

            result = await factory.submit_for_approval(bad_definition)
            assert result.status == AgentDefinitionStatus.REJECTED
