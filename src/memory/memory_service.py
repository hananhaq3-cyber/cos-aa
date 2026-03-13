"""
Unified Memory Service facade.
Single entry point for all memory operations across all 4 tiers.
"""
import asyncio
from uuid import UUID

from src.core.domain_objects import MemoryFragment
from src.memory.episodic_memory import episodic_memory_store
from src.memory.procedural_memory import procedural_memory_store
from src.memory.retrieval_ranker import rank_results
from src.memory.semantic_memory import SemanticMemoryStore, create_semantic_memory_store
from src.memory.working_memory import working_memory_store


class MemoryService:
    """Unified facade for all 4 memory tiers."""

    def __init__(self):
        self._semantic: SemanticMemoryStore | None = None

    @property
    def semantic(self) -> SemanticMemoryStore:
        if self._semantic is None:
            self._semantic = create_semantic_memory_store()
        return self._semantic

    # ── Working Memory ──

    async def read_working_memory(
        self, tenant_id: UUID, session_id: UUID, agent_id: UUID
    ) -> dict | None:
        return await working_memory_store.read(tenant_id, session_id, agent_id)

    async def update_working_memory(
        self, tenant_id: UUID, session_id: UUID, agent_id: UUID, state: dict
    ) -> None:
        await working_memory_store.write(tenant_id, session_id, agent_id, state)

    async def flush_working_memory(
        self, tenant_id: UUID, session_id: UUID, agent_id: UUID
    ) -> dict | None:
        return await working_memory_store.flush(tenant_id, session_id, agent_id)

    # ── Episodic Memory ──

    async def write_episodic(
        self,
        tenant_id: UUID,
        session_id: UUID,
        agent_id: UUID,
        event_type: str,
        content: dict,
        **kwargs,
    ) -> UUID:
        return await episodic_memory_store.write_event(
            tenant_id, session_id, agent_id, event_type, content, **kwargs
        )

    async def query_episodic(
        self, tenant_id: UUID, limit: int = 20, **kwargs
    ) -> list[dict]:
        return await episodic_memory_store.query_recent(
            tenant_id, limit, **kwargs
        )

    # ── Semantic Memory ──

    async def store_semantic(
        self, tenant_id: UUID, content: str, **kwargs
    ) -> str:
        return await self.semantic.store(tenant_id, content, **kwargs)

    async def search_semantic(
        self, tenant_id: UUID, query: str, top_k: int = 20, **kwargs
    ):
        return await self.semantic.search(tenant_id, query, top_k, **kwargs)

    # ── Procedural Memory ──

    async def find_pattern(
        self, tenant_id: UUID, task_type: str
    ) -> dict | None:
        return await procedural_memory_store.find_best_pattern(
            tenant_id, task_type
        )

    async def store_pattern(self, tenant_id: UUID, **kwargs) -> None:
        await procedural_memory_store.store_pattern(tenant_id, **kwargs)

    # ── Hybrid Retrieval (used by ORIENT phase) ──

    async def retrieve_context(
        self,
        tenant_id: UUID,
        query: str,
        session_id: UUID | None = None,
        top_k: int = 5,
    ) -> list[MemoryFragment]:
        semantic_task = self.search_semantic(tenant_id, query, top_k=20)
        episodic_task = self.query_episodic(
            tenant_id, limit=20, session_id=session_id
        )

        semantic_results, episodic_results = await asyncio.gather(
            semantic_task, episodic_task
        )

        return rank_results(
            semantic_results, episodic_results, query, top_k=top_k
        )


memory_service = MemoryService()
