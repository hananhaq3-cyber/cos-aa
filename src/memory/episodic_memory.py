"""
Episodic Memory: long-term storage of events, task outcomes, actions.
Stored in PostgreSQL with RLS per tenant.
"""
from uuid import UUID

import orjson
from sqlalchemy import text

from src.db.postgres import get_session


class EpisodicMemoryStore:
    """PostgreSQL-backed episodic memory operations."""

    async def write_event(
        self,
        tenant_id: UUID,
        session_id: UUID,
        agent_id: UUID,
        event_type: str,
        content: dict,
        user_id: UUID | None = None,
        importance_score: float = 0.5,
        embedding_id: str | None = None,
        tags: list[str] | None = None,
    ) -> UUID:
        async with get_session(tenant_id) as session:
            result = await session.execute(
                text("""
                    INSERT INTO episodic_memories
                        (tenant_id, user_id, agent_id, session_id, event_type, content,
                         importance_score, embedding_id, tags)
                    VALUES
                        (:tenant_id, :user_id, :agent_id, :session_id, :event_type,
                         :content::jsonb, :importance, :embedding_id, :tags)
                    RETURNING id
                """),
                {
                    "tenant_id": str(tenant_id),
                    "user_id": str(user_id) if user_id else None,
                    "agent_id": str(agent_id),
                    "session_id": str(session_id),
                    "event_type": event_type,
                    "content": orjson.dumps(content).decode(),
                    "importance": importance_score,
                    "embedding_id": embedding_id,
                    "tags": tags,
                },
            )
            row = result.fetchone()
            return UUID(str(row[0]))

    async def query_recent(
        self,
        tenant_id: UUID,
        limit: int = 20,
        session_id: UUID | None = None,
        agent_id: UUID | None = None,
        event_type: str | None = None,
        min_importance: float = 0.0,
    ) -> list[dict]:
        filters = [
            "tenant_id = :tenant_id",
            "importance_score >= :min_importance",
        ]
        params: dict = {
            "tenant_id": str(tenant_id),
            "min_importance": min_importance,
        }

        if session_id:
            filters.append("session_id = :session_id")
            params["session_id"] = str(session_id)
        if agent_id:
            filters.append("agent_id = :agent_id")
            params["agent_id"] = str(agent_id)
        if event_type:
            filters.append("event_type = :event_type")
            params["event_type"] = event_type

        where_clause = " AND ".join(filters)
        query = f"""
            SELECT id, event_type, content, importance_score, created_at, tags
            FROM episodic_memories
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit
        """
        params["limit"] = limit

        async with get_session(tenant_id) as session:
            result = await session.execute(text(query), params)
            rows = result.fetchall()
            return [
                {
                    "id": str(row[0]),
                    "event_type": row[1],
                    "content": row[2],
                    "importance_score": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "tags": row[5] or [],
                }
                for row in rows
            ]

    async def increment_access(
        self, tenant_id: UUID, memory_id: UUID
    ) -> None:
        async with get_session(tenant_id) as session:
            await session.execute(
                text("""
                    UPDATE episodic_memories
                    SET access_count = access_count + 1, accessed_at = NOW()
                    WHERE id = :id AND tenant_id = :tenant_id
                """),
                {"id": str(memory_id), "tenant_id": str(tenant_id)},
            )


episodic_memory_store = EpisodicMemoryStore()
