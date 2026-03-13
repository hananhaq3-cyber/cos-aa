"""
Sample messages and payloads for testing.
"""
from uuid import uuid4

from src.core.domain_objects import (
    AgentType,
    GoalObject,
    InputModality,
    InputSource,
    ObservationObject,
    ObservationSet,
    Priority,
)
from src.core.message_schemas import (
    AgentMessage,
    MessageType,
    TaskDispatchPayload,
    TaskResultPayload,
)


def make_user_message(content: str = "Help me prepare for my AI exam") -> ObservationObject:
    return ObservationObject(
        source_type=InputSource.USER,
        content=content,
        raw_content=content,
        modality=InputModality.TEXT,
        relevance_score=1.0,
    )


def make_observation_set(content: str = "Help me prepare for my AI exam") -> ObservationSet:
    return ObservationSet(observations=[make_user_message(content)])


def make_goal(description: str = "Help the user prepare for their AI exam") -> GoalObject:
    return GoalObject(
        description=description,
        success_criteria=["Study plan generated", "Key topics identified"],
        priority=Priority.NORMAL,
        max_iterations=5,
        timeout_seconds=120,
    )


def make_task_dispatch(
    task_type: str = "knowledge_retrieval",
    agent_type: AgentType = AgentType.KNOWLEDGE,
) -> TaskDispatchPayload:
    return TaskDispatchPayload(
        task_id=uuid4(),
        session_id=uuid4(),
        agent_type=agent_type.value,
        task_type=task_type,
        input_data={"query": "What are key topics in AI?", "tenant_id": str(uuid4())},
        priority="NORMAL",
        timeout_seconds=60,
    )


def make_task_result(task_id=None, success: bool = True) -> TaskResultPayload:
    return TaskResultPayload(
        task_id=task_id or uuid4(),
        success=success,
        output={"answer": "Machine Learning, Neural Networks, NLP", "confidence": "high"},
        duration_ms=1500.0,
        tokens_consumed=200,
    )


def make_agent_message(
    msg_type: MessageType = MessageType.TASK_DISPATCH,
) -> AgentMessage:
    return AgentMessage(
        sender_agent_type=AgentType.HUB.value,
        target_agent_type=AgentType.KNOWLEDGE.value,
        message_type=msg_type,
        payload={"task_type": "knowledge_retrieval"},
        session_id=uuid4(),
        tenant_id=uuid4(),
    )
