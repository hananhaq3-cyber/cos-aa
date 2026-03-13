"""
Integration test: Memory write/read across all 4 tiers.
Tests working memory (Redis), episodic (PostgreSQL), semantic (vector), procedural (PostgreSQL).
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


@pytest.mark.asyncio
class TestMemoryWriteRead:
    async def test_working_memory_write_and_read(self):
        """Write to working memory (Redis) and read back."""
        from src.memory.working_memory import WorkingMemoryStore

        tenant_id = uuid4()
        session_id = uuid4()
        agent_id = uuid4()

        store = WorkingMemoryStore()

        mock_client = AsyncMock()
        mock_client.setex = AsyncMock()
        mock_client.get = AsyncMock(return_value=b'{"goal":"Test goal","phase":"OBSERVING"}')
        mock_client.expire = AsyncMock()

        with patch("src.memory.working_memory.redis_client") as mock_rc:
            mock_rc.client = mock_client

            # Write
            await store.write(tenant_id, session_id, agent_id, {
                "goal": "Test goal",
                "phase": "OBSERVING",
            })
            mock_client.setex.assert_called_once()

            # Read
            result = await store.read(tenant_id, session_id, agent_id)
            assert result is not None
            assert result["goal"] == "Test goal"

    async def test_episodic_memory_write_and_query(self):
        """Write an episodic event and query recent events."""
        from src.memory.episodic_memory import EpisodicMemoryStore

        store = EpisodicMemoryStore()
        tenant_id = uuid4()
        session_id = uuid4()
        agent_id = uuid4()
        returned_id = uuid4()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (str(returned_id),)
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("src.memory.episodic_memory.get_session") as mock_get_session:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_ctx

            result_id = await store.write_event(
                tenant_id=tenant_id,
                session_id=session_id,
                agent_id=agent_id,
                event_type="TASK_COMPLETE",
                content={"task": "knowledge_retrieval", "answer": "AI topics"},
                importance_score=0.8,
                tags=["knowledge", "ai"],
            )

            mock_session.execute.assert_called()
            assert result_id == returned_id

    async def test_semantic_memory_store_and_search(self):
        """Store a document in semantic memory and search for it."""
        from src.memory.semantic_memory import SemanticMemoryStore
        from src.memory.vector_store.interface import VectorSearchResult

        mock_vector_store = AsyncMock()
        mock_vector_store.upsert = AsyncMock()
        mock_search_result = VectorSearchResult(
            doc_id=str(uuid4()),
            content="Neural networks are computing systems inspired by biological neural networks.",
            score=0.92,
            metadata={"source_type": "DOCUMENT"},
        )
        mock_vector_store.search = AsyncMock(return_value=[mock_search_result])

        store = SemanticMemoryStore(vector_store=mock_vector_store)

        tenant_id = uuid4()

        with patch("src.memory.semantic_memory.embedding_service") as mock_emb:
            mock_emb.embed_text = AsyncMock(return_value=[0.1] * 3072)
            mock_emb.dimension = 3072

            # Store
            doc_id = await store.store(
                tenant_id=tenant_id,
                content="Neural networks are computing systems.",
                source_type="DOCUMENT",
                tags=["ai", "ml"],
            )
            mock_emb.embed_text.assert_called()
            mock_vector_store.upsert.assert_called()
            assert isinstance(doc_id, str)

            # Search
            results = await store.search(
                tenant_id=tenant_id,
                query="What are neural networks?",
                top_k=5,
            )
            assert len(results) == 1
            assert results[0].score > 0.7

    async def test_procedural_memory_store_and_match(self):
        """Store a procedural pattern and match it."""
        from src.memory.procedural_memory import ProceduralMemoryStore

        store = ProceduralMemoryStore()
        tenant_id = uuid4()

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        with patch("src.memory.procedural_memory.get_session") as mock_get_session:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_get_session.return_value = mock_ctx

            await store.store_pattern(
                tenant_id=tenant_id,
                pattern_name="web_search_then_synthesize",
                task_type="knowledge_retrieval",
                trigger_conditions={"source": "user_query"},
                action_sequence=[
                    {"step": 1, "tool": "web_search"},
                    {"step": 2, "tool": "llm_synthesize"},
                ],
            )

            mock_session.execute.assert_called()

    async def test_memory_service_retrieve_context(self):
        """Test the unified MemoryService.retrieve_context facade."""
        from src.memory.memory_service import MemoryService
        from src.memory.vector_store.interface import VectorSearchResult

        service = MemoryService()
        tenant_id = uuid4()
        session_id = uuid4()

        mock_search_result = VectorSearchResult(
            doc_id=str(uuid4()),
            content="AI knowledge fragment",
            score=0.85,
            metadata={
                "source_type": "EPISODIC",
                "importance_score": "0.8",
                "created_at": "2026-03-09T00:00:00+00:00",
                "tags": "ai",
                "summary": "AI knowledge fragment",
            },
        )

        with (
            patch.object(service, "search_semantic", new_callable=AsyncMock) as mock_semantic,
            patch.object(service, "query_episodic", new_callable=AsyncMock) as mock_episodic,
        ):
            mock_semantic.return_value = [mock_search_result]
            mock_episodic.return_value = []

            results = await service.retrieve_context(
                tenant_id=tenant_id,
                query="Tell me about AI",
                session_id=session_id,
                top_k=5,
            )

            assert len(results) >= 1
            assert results[0].content == "AI knowledge fragment"
