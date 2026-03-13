"""Pinecone implementation for production and large tenants."""
from pinecone import Pinecone, ServerlessSpec

from src.core.config import settings
from src.memory.vector_store.interface import (
    VectorStoreInterface,
    VectorDocument,
    VectorSearchResult,
)


class PineconeAdapter(VectorStoreInterface):

    def __init__(self):
        self._pc = Pinecone(api_key=settings.pinecone_api_key)
        self._indexes: dict = {}

    def _get_index(self, collection_name: str):
        if collection_name not in self._indexes:
            self._indexes[collection_name] = self._pc.Index(collection_name)
        return self._indexes[collection_name]

    async def create_collection(self, collection_name: str, dimension: int) -> None:
        existing = [idx.name for idx in self._pc.list_indexes()]
        if collection_name not in existing:
            self._pc.create_index(
                name=collection_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws", region=settings.pinecone_environment
                ),
            )

    async def upsert(
        self, collection_name: str, documents: list[VectorDocument]
    ) -> None:
        index = self._get_index(collection_name)
        vectors = [
            {
                "id": d.doc_id,
                "values": d.embedding,
                "metadata": {**d.metadata, "_content": d.content[:40000]},
            }
            for d in documents
        ]
        for i in range(0, len(vectors), 100):
            index.upsert(vectors=vectors[i : i + 100])

    async def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 10,
        filter_metadata: dict | None = None,
    ) -> list[VectorSearchResult]:
        index = self._get_index(collection_name)
        kwargs: dict = {
            "vector": query_embedding,
            "top_k": top_k,
            "include_metadata": True,
        }
        if filter_metadata:
            kwargs["filter"] = filter_metadata
        results = index.query(**kwargs)

        return [
            VectorSearchResult(
                doc_id=match["id"],
                content=match.get("metadata", {}).get("_content", ""),
                score=match["score"],
                metadata={
                    k: v
                    for k, v in match.get("metadata", {}).items()
                    if k != "_content"
                },
            )
            for match in results.get("matches", [])
        ]

    async def delete(self, collection_name: str, doc_ids: list[str]) -> None:
        index = self._get_index(collection_name)
        index.delete(ids=doc_ids)

    async def health_check(self) -> bool:
        try:
            self._pc.list_indexes()
            return True
        except Exception:
            return False
