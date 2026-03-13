"""
Anthropic Claude client — fallback when OpenAI is unavailable.
"""
from typing import Any

import orjson
from anthropic import AsyncAnthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from src.core.config import settings
from src.core.exceptions import CoTParsingError, LLMCallError
from src.llm.llm_client import LLMClient, LLMResponse


class AnthropicClient(LLMClient):

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        self._client = AsyncAnthropic(
            api_key=api_key or settings.anthropic_api_key
        )
        self._default_model = model

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
            system_msg = ""
            chat_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    chat_messages.append(msg)

            kwargs: dict[str, Any] = {
                "model": model or self._default_model,
                "messages": chat_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if system_msg:
                kwargs["system"] = system_msg
            if stop:
                kwargs["stop_sequences"] = stop

            response = await self._client.messages.create(**kwargs)

            content = response.content[0].text if response.content else ""
            return LLMResponse(
                content=content,
                model=response.model,
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens
                + response.usage.output_tokens,
                finish_reason=response.stop_reason or "end_turn",
                raw_response=response.model_dump(),
            )
        except Exception as e:
            raise LLMCallError("anthropic", str(e))

    async def chat_completion_json(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        json_instruction = (
            "\n\nYou MUST respond with valid JSON only. "
            "No markdown, no explanation, just JSON."
        )
        augmented = []
        system_found = False
        for msg in messages:
            if msg["role"] == "system":
                augmented.append(
                    {
                        "role": "system",
                        "content": msg["content"] + json_instruction,
                    }
                )
                system_found = True
            else:
                augmented.append(msg)
        if not system_found:
            augmented.insert(
                0, {"role": "system", "content": json_instruction.strip()}
            )

        response = await self.chat_completion(
            messages=augmented,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            return orjson.loads(response.content)
        except (orjson.JSONDecodeError, ValueError) as e:
            raise CoTParsingError(
                f"Anthropic returned invalid JSON: {e}\nRaw: {response.content[:500]}"
            )

    async def health_check(self) -> bool:
        try:
            response = await self._client.messages.create(
                model=self._default_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return len(response.content) > 0
        except Exception:
            return False
