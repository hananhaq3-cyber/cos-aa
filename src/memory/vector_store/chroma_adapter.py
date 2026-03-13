"""ChromaDB implementation for development and small tenants."""
import chromadb
from chromadb.config import Settings as ChromaSettings

from src.core.config import settings
from src.memory.vector_store.interface import (
    VectorStoreInterface,
    VectorDocument,
    VectorSearchResult,
)


class ChromaAdapter(VectorStoreInterface):

    def __init__(self):
        self._client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    async def create_collection(self, collection_name: str, dimension: int) -> None:
        self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    async def upsert(
        self, collection_name: str, documents: list[VectorDocument]
    ) -> None:
        collection = self._client.get_or_create_collection(name=collection_name)
        collection.upsert(
            ids=[d.doc_id for d in documents],
            embeddings=[d.embedding for d in documents],
            documents=[d.content for d in documents],
            metadatas=[d.metadata for d in documents],
        )

    async def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 10,
        filter_metadata: dict | None = None,
    ) -> list[VectorSearchResult]:
        collection = self._client.get_or_create_collection(name=collection_name)
        kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
        }
        if filter_metadata:
            kwargs["where"] = filter_metadata
        results = collection.query(**kwargs)

        output: list[VectorSearchResult] = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                output.append(
                    VectorSearchResult(
                        doc_id=doc_id,
                        content=(
                            results["documents"][0][i]
                            if results["documents"]
                            else ""
                        ),
                        score=1.0
                        - (
                            results["distances"][0][i]
                            if results["distances"]
                            else 0.0
                        ),
                        metadata=(
                            results["metadatas"][0][i]
                            if results["metadatas"]
                            else {}
                        ),
                    )
                )
        return output

    async def delete(self, collection_name: str, doc_ids: list[str]) -> None:
        collection = self._client.get_collection(name=collection_name)
        collection.delete(ids=doc_ids)

    async def health_check(self) -> bool:
        try:
            self._client.heartbeat()
            return True
        except Exception:
            return False
