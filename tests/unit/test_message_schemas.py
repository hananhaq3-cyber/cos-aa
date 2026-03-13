"""
Unit tests for message schema serialization/deserialization.
"""
import json
from uuid import uuid4

import pytest

from src.core.domain_objects import AgentRef, AgentType, Priority
from src.core.message_schemas import (
    AgentMessage,
    BroadcastRef,
    MessageType,
    TaskDispatchPayload,
    TaskFailurePayload,
    TaskResultPayload,
    SpawnAgentRequestPayload,
    HeartbeatPayload,
)


class TestAgentMessage:
    def test_create_with_defaults(self):
        msg = AgentMessage(
            sender=AgentRef(agent_type=AgentType.HUB),
            recipient=AgentRef(agent_type=AgentType.KNOWLEDGE),
            message_type=MessageType.TASK_DISPATCH,
            payload={"task_type": "search"},
            tenant_id=uuid4(),
        )
        assert msg.message_type == MessageType.TASK_DISPATCH
        assert msg.message_id is not None
        assert msg.created_at is not None

    def test_serialization_roundtrip(self):
        msg = AgentMessage(
            sender=AgentRef(agent_type=AgentType.HUB),
            recipient=AgentRef(agent_type=AgentType.PLANNING),
            message_type=MessageType.TASK_RESULT,
            payload={"success": True, "output": "done"},
            tenant_id=uuid4(),
        )
        dumped = msg.model_dump_json()
        loaded = AgentMessage.model_validate_json(dumped)
        assert loaded.message_id == msg.message_id
        assert loaded.message_type == msg.message_type
        assert loaded.payload == msg.payload


class TestTaskDispatchPayload:
    def test_creation(self):
        payload = TaskDispatchPayload(
            task_id=uuid4(),
            session_id=uuid4(),
            goal_id=uuid4(),
            task_type="web_search",
            input_data={"query": "test"},
            timeout_seconds=30,
        )
        assert payload.timeout_seconds == 30

    def test_serialization(self):
        payload = TaskDispatchPayload(
            task_id=uuid4(),
            session_id=uuid4(),
            goal_id=uuid4(),
            task_type="plan",
            input_data={"goal": "test goal"},
        )
        data = payload.model_dump()
        assert "task_id" in data
        assert data["task_type"] == "plan"


class TestTaskResultPayload:
    def test_success_result(self):
        result = TaskResultPayload(
            task_id=uuid4(),
            success=True,
            output={"answer": "42"},
            duration_ms=1500.0,
            tokens_consumed=200,
        )
        assert result.success is True
        assert result.duration_ms == 1500.0

    def test_failure_result(self):
        result = TaskResultPayload(
            task_id=uuid4(),
            success=False,
            output=None,
            duration_ms=60000.0,
        )
        assert result.success is False
        assert result.output is None


class TestTaskFailurePayload:
    def test_creation(self):
        payload = TaskFailurePayload(
            task_id=uuid4(),
            error_code="CAPABILITY_MISSING",
            failure_type="CAPABILITY_MISSING",
            error_message="No agent can handle this task type",
        )
        assert payload.failure_type == "CAPABILITY_MISSING"
        assert payload.error_code == "CAPABILITY_MISSING"


class TestSpawnAgentRequestPayload:
    def test_creation(self):
        payload = SpawnAgentRequestPayload(
            tenant_id=uuid4(),
            task_type="financial_analysis",
            gap_description="Need a financial analysis agent",
            sample_task_ids=[uuid4(), uuid4()],
        )
        assert len(payload.sample_task_ids) == 2
        assert payload.task_type == "financial_analysis"


class TestHeartbeatPayload:
    def test_creation(self):
        payload = HeartbeatPayload(
            agent_id=uuid4(),
            current_task_count=2,
            max_concurrent_tasks=5,
            healthy=True,
        )
        assert payload.healthy is True
        assert payload.current_task_count == 2
