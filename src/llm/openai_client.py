"""
OpenAI LLM client with retry, circuit breaker, and structured JSON output.
"""
from typing import Any

import orjson
from openai import AsyncOpenAI
from pybreaker import CircuitBreaker
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from src.core.config import settings
from src.core.exceptions import CoTParsingError, LLMCallError
from src.llm.llm_client import LLMClient, LLMResponse

_circuit_breaker = CircuitBreaker(fail_max=5, reset_timeout=30)


class OpenAIClient(LLMClient):
    """OpenAI GPT-4o implementation with built-in reliability."""

    def __init__(
        self, api_key: str | None = None, model: str | None = None
    ):
        self._client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key
        )
        self._default_model = model or settings.llm_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=30),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: dict | None = None,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        try:
            kwargs: dict[str, Any] = {
                "model": model or self._default_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                kwargs["response_format"] = response_format
            if stop:
                kwargs["stop"] = stop

            response = await _circuit_breaker.call_async(
                self._client.chat.completions.create, **kwargs
            )

            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                finish_reason=choice.finish_reason or "stop",
                raw_response=response.model_dump(),
            )
        except Exception as e:
            if "CircuitBreakerError" in type(e).__name__:
                raise LLMCallError(
                    "openai",
                    "Circuit breaker is open — too many recent failures",
                )
            raise LLMCallError("openai", str(e))

    async def chat_completion_json(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        response = await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        try:
            return orjson.loads(response.content)
        except (orjson.JSONDecodeError, ValueError) as e:
            raise CoTParsingError(
                f"LLM returned invalid JSON: {e}\nRaw: {response.content[:500]}"
            )

    async def health_check(self) -> bool:
        try:
            response = await self._client.chat.completions.create(
                model=self._default_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return response.choices[0].message.content is not None
        except Exception:
            return False
