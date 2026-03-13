"""
Abstract interface for vector stores. Implementations: Chroma (dev), Pinecone (prod).
"""
from abc import ABC, abstractmethod
from uuid import UUID


class VectorDocument:
    """A document with its embedding and metadata."""

    def __init__(
        self,
        doc_id: str,
        content: str,
        embedding: list[float],
        metadata: dict,
    ):
        self.doc_id = doc_id
        self.content = content
        self.embedding = embedding
        self.metadata = metadata


class VectorSearchResult:
    """A single search result from the vector store."""

    def __init__(
        self,
        doc_id: str,
        content: str,
        score: float,
        metadata: dict,
    ):
        self.doc_id = doc_id
        self.content = content
        self.score = score
        self.metadata = metadata


class VectorStoreInterface(ABC):
    """Abstract interface for all vector store backends."""

    @abstractmethod
    async def create_collection(self, collection_name: str, dimension: int) -> None:
        """Create a new vector collection/namespace."""

    @abstractmethod
    async def upsert(
        self, collection_name: str, documents: list[VectorDocument]
    ) -> None:
        """Insert or update documents in a collection."""

    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 10,
        filter_metadata: dict | None = None,
    ) -> list[VectorSearchResult]:
        """Search for similar documents by embedding."""

    @abstractmethod
    async def delete(self, collection_name: str, doc_ids: list[str]) -> None:
        """Delete documents from a collection."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check connectivity to the vector store."""

    @staticmethod
    def tenant_collection(tenant_id: UUID, suffix: str = "semantic") -> str:
        """Generate the tenant-scoped collection name."""
        return f"{tenant_id}_{suffix}"
