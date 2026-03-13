"""
Integration test: HUB -> Broker -> Agent -> Result flow.
Uses mocked Celery to avoid needing a running Redis instance.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.core.domain_objects import AgentType, Priority
from src.core.message_schemas import TaskDispatchPayload


@pytest.mark.asyncio
class TestHubToAgentFlow:
    async def test_dispatch_and_receive_result(self):
        """Test that HUB can dispatch a task and receive a result."""
        from src.messaging.dispatcher import TaskDispatcher

        with patch("src.messaging.dispatcher.celery_app") as mock_celery:
            mock_result = MagicMock()
            mock_result.id = str(uuid4())
            mock_celery.send_task = MagicMock(return_value=mock_result)

            dispatcher = TaskDispatcher()
            tenant_id = uuid4()
            session_id = uuid4()
            goal_id = uuid4()

            payload = TaskDispatchPayload(
                task_type="knowledge_retrieval",
                goal_id=goal_id,
                session_id=session_id,
                input_data={"query": "What is AI?"},
            )

            task_id = dispatcher.dispatch_task(
                tenant_id=tenant_id,
                agent_type=AgentType.KNOWLEDGE,
                payload=payload,
                priority=Priority.NORMAL,
            )

            assert task_id is not None
            mock_celery.send_task.assert_called_once()

    async def test_dispatch_parallel_tasks(self):
        """Test parallel task dispatch to multiple agents."""
        from src.messaging.dispatcher import TaskDispatcher

        with patch("src.messaging.dispatcher.celery_app") as mock_celery:
            call_count = 0

            def mock_send(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                result = MagicMock()
                result.id = str(uuid4())
                return result

            mock_celery.send_task = mock_send

            dispatcher = TaskDispatcher()
            tenant_id = uuid4()
            session_id = uuid4()
            goal_id = uuid4()

            tasks = [
                (
                    tenant_id,
                    AgentType.KNOWLEDGE,
                    TaskDispatchPayload(
                        task_type="web_search",
                        goal_id=goal_id,
                        session_id=session_id,
                        input_data={"query": "AI topics"},
                    ),
                    Priority.NORMAL,
                ),
                (
                    tenant_id,
                    AgentType.PLANNING,
                    TaskDispatchPayload(
                        task_type="plan_generation",
                        goal_id=goal_id,
                        session_id=session_id,
                        input_data={"goal": "Create study plan"},
                    ),
                    Priority.NORMAL,
                ),
            ]

            results = dispatcher.dispatch_parallel(tasks=tasks)

            assert call_count == 2
            assert len(results) == 2
