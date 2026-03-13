"""
Embedding generation via OpenAI text-embedding-3-large.
Also provides the get_llm_client() factory function.
"""
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from src.core.config import settings


class EmbeddingService:
    """Generates embeddings using OpenAI's embedding API."""

    def __init__(
        self, api_key: str | None = None, model: str | None = None
    ):
        self._client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key
        )
        self._model = model or settings.embedding_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=15),
    )
    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text string."""
        response = await self._client.embeddings.create(
            model=self._model,
            input=text,
        )
        return response.data[0].embedding

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=15),
    )
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in one API call."""
        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    @property
    def dimension(self) -> int:
        """Return embedding dimension for the configured model."""
        dimensions = {
            "text-embedding-3-large": 3072,
            "text-embedding-3-small": 1536,
            "text-embedding-ada-002": 1536,
        }
        return dimensions.get(self._model, 3072)


def get_llm_client():
    """Return the configured LLM client based on settings."""
    if settings.llm_provider == "anthropic":
        from src.llm.anthropic_client import AnthropicClient

        return AnthropicClient()
    from src.llm.openai_client import OpenAIClient

    return OpenAIClient()


# Singleton instances
embedding_service = EmbeddingService()
