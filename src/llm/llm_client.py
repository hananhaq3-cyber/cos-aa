"""
Provider-agnostic LLM client interface.
Every LLM integration implements this ABC.
"""
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Standardized response from any LLM provider."""

    content: str | dict[str, Any]
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = "stop"
    raw_response: dict[str, Any] = {}


class LLMClient(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: dict | None = None,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """Send a chat completion request."""

    @abstractmethod
    async def chat_completion_json(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Send a chat completion that MUST return valid JSON."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify connectivity to the LLM provider."""
