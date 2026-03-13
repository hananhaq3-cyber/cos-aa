"""
Nightly memory consolidation: promote important episodic entries to semantic,
decay old memory importance scores, archive cold memories.
Runs as a Celery beat scheduled task.
"""
from uuid import UUID

from sqlalchemy import text

from src.db.postgres import get_session
from src.memory.semantic_memory import create_semantic_memory_store

IMPORTANCE_PROMOTION_THRESHOLD = 0.7
ARCHIVE_AGE_DAYS = 90
ARCHIVE_MIN_ACCESS_COUNT = 2
FORGETTING_THRESHOLD = 0.1


async def consolidate_tenant_memory(tenant_id: UUID) -> dict:
    stats = {"promoted": 0, "decayed": 0, "archived": 0}
    semantic = create_semantic_memory_store()

    async with get_session(tenant_id) as session:
        # 1. Promote high-importance episodic → semantic
        result = await session.execute(
            text("""
                SELECT id, content, importance_score, tags
                FROM episodic_memories
                WHERE tenant_id = :tid
                  AND importance_score >= :threshold
                  AND embedding_id IS NULL
                ORDER BY importance_score DESC
                LIMIT 50
            """),
            {
                "tid": str(tenant_id),
                "threshold": IMPORTANCE_PROMOTION_THRESHOLD,
            },
        )
        rows = result.fetchall()
        for row in rows:
            content_str = str(row[1])
            embedding_id = await semantic.store(
                tenant_id,
                content_str,
                summary=content_str[:200],
                source_type="EPISODIC",
                tags=row[3] or [],
            )
            await session.execute(
                text(
                    "UPDATE episodic_memories SET embedding_id = :eid WHERE id = :id"
                ),
                {"eid": embedding_id, "id": str(row[0])},
            )
            stats["promoted"] += 1

        # 2. Decay old low-access importance scores
        await session.execute(
            text("""
                UPDATE episodic_memories
                SET importance_score = importance_score * 0.95
                WHERE tenant_id = :tid
                  AND created_at < NOW() - INTERVAL '30 days'
                  AND access_count < 5
                  AND importance_score > :floor
            """),
            {"tid": str(tenant_id), "floor": FORGETTING_THRESHOLD},
        )

        # 3. Archive very old, unreferenced memories
        result = await session.execute(
            text(f"""
                DELETE FROM episodic_memories
                WHERE tenant_id = :tid
                  AND created_at < NOW() - INTERVAL '{ARCHIVE_AGE_DAYS} days'
                  AND access_count < :min_access
                  AND importance_score < :threshold
                RETURNING id
            """),
            {
                "tid": str(tenant_id),
                "min_access": ARCHIVE_MIN_ACCESS_COUNT,
                "threshold": FORGETTING_THRESHOLD,
            },
        )
        stats["archived"] = len(result.fetchall())

    return stats
