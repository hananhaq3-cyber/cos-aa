"""
Semantic Memory: vectorized knowledge stored in Chroma/Pinecone.
Delegates to VectorStoreInterface for backend-agnostic operations.
"""
from uuid import UUID, uuid4

from src.core.config import settings
from src.llm.embeddings import embedding_service
from src.memory.vector_store.interface import (
    VectorStoreInterface,
    VectorDocument,
    VectorSearchResult,
)


class SemanticMemoryStore:
    """High-level semantic memory operations using vector store + embeddings."""

    def __init__(self, vector_store: VectorStoreInterface):
        self._store = vector_store

    async def initialize_tenant(self, tenant_id: UUID) -> None:
        collection = VectorStoreInterface.tenant_collection(tenant_id)
        await self._store.create_collection(collection, embedding_service.dimension)

    async def store(
        self,
        tenant_id: UUID,
        content: str,
        summary: str = "",
        source_type: str = "EPISODIC",
        tags: list[str] | None = None,
    ) -> str:
        doc_id = str(uuid4())
        embedding = await embedding_service.embed_text(content)
        collection = VectorStoreInterface.tenant_collection(tenant_id)

        doc = VectorDocument(
            doc_id=doc_id,
            content=content,
            embedding=embedding,
            metadata={
                "summary": summary or content[:200],
                "source_type": source_type,
                "tags": ",".join(tags or []),
                "tenant_id": str(tenant_id),
            },
        )
        await self._store.upsert(collection, [doc])
        return doc_id

    async def search(
        self,
        tenant_id: UUID,
        query: str,
        top_k: int = 20,
        source_type_filter: str | None = None,
        tag_filter: str | None = None,
    ) -> list[VectorSearchResult]:
        query_embedding = await embedding_service.embed_text(query)
        collection = VectorStoreInterface.tenant_collection(tenant_id)

        filters = {}
        if source_type_filter:
            filters["source_type"] = source_type_filter
        if tag_filter:
            filters["tags"] = {"$contains": tag_filter}

        return await self._store.search(
            collection,
            query_embedding,
            top_k=top_k,
            filter_metadata=filters if filters else None,
        )

    async def delete(self, tenant_id: UUID, doc_ids: list[str]) -> None:
        collection = VectorStoreInterface.tenant_collection(tenant_id)
        await self._store.delete(collection, doc_ids)


def create_semantic_memory_store() -> SemanticMemoryStore:
    if settings.vector_backend == "pinecone":
        from src.memory.vector_store.pinecone_adapter import PineconeAdapter

        return SemanticMemoryStore(PineconeAdapter())
    from src.memory.vector_store.chroma_adapter import ChromaAdapter

    return SemanticMemoryStore(ChromaAdapter())
