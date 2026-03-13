"""
Shared pytest fixtures: mock LLM, test database, Redis, and session factories.
"""
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio

from src.core.config import settings
from src.core.domain_objects import AgentType, OODAPhase, Priority


# ─── Event Loop ───

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ─── Test IDs ───

@pytest.fixture
def tenant_id():
    return uuid4()


@pytest.fixture
def session_id():
    return uuid4()


@pytest.fixture
def user_id():
    return uuid4()


# ─── Mock LLM Client ───

@pytest.fixture
def mock_llm_client():
    """Returns a mock LLM client with configurable responses."""
    from src.llm.llm_client import LLMResponse

    client = AsyncMock()
    client.chat_completion = AsyncMock(
        return_value=LLMResponse(
            content="Mock LLM response",
            model="gpt-4o-test",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
    )
    client.chat_completion_json = AsyncMock(
        return_value=LLMResponse(
            content={"answer": "mock answer", "confidence": 0.9},
            model="gpt-4o-test",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
    )
    client.health_check = AsyncMock(return_value=True)
    return client


# ─── Mock Redis ───

@pytest.fixture
def mock_redis():
    """Returns a mock Redis client."""
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.hgetall = AsyncMock(return_value={})
    redis.hset = AsyncMock(return_value=1)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.publish = AsyncMock(return_value=1)
    redis.info = AsyncMock(return_value={"used_memory": 1024000})
    redis.sadd = AsyncMock(return_value=1)
    redis.smembers = AsyncMock(return_value=set())
    redis.scan_iter = AsyncMock(return_value=iter([]))
    return redis


# ─── Mock Database Session ───

@pytest.fixture
def mock_db_session():
    """Returns a mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session
