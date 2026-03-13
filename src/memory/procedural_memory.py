"""
Procedural Memory: stores successful workflows, tool usage patterns.
Queried during ORIENT to find matching action patterns for a task type.
"""
from uuid import UUID

import orjson
from sqlalchemy import text

from src.db.postgres import get_session


class ProceduralMemoryStore:

    async def store_pattern(
        self,
        tenant_id: UUID,
        pattern_name: str,
        task_type: str,
        trigger_conditions: dict,
        action_sequence: list[dict],
    ) -> None:
        async with get_session(tenant_id) as session:
            await session.execute(
                text("""
                    INSERT INTO procedural_patterns
                        (tenant_id, pattern_name, task_type, trigger_conditions, action_sequence)
                    VALUES (:tid, :name, :task_type, :triggers::jsonb, :actions::jsonb)
                    ON CONFLICT (tenant_id, pattern_name) DO UPDATE SET
                        action_sequence = EXCLUDED.action_sequence,
                        last_used_at = NOW()
                """),
                {
                    "tid": str(tenant_id),
                    "name": pattern_name,
                    "task_type": task_type,
                    "triggers": orjson.dumps(trigger_conditions).decode(),
                    "actions": orjson.dumps(action_sequence).decode(),
                },
            )

    async def find_best_pattern(
        self, tenant_id: UUID, task_type: str
    ) -> dict | None:
        async with get_session(tenant_id) as session:
            result = await session.execute(
                text("""
                    SELECT pattern_name, task_type, trigger_conditions, action_sequence,
                           success_count, failure_count, avg_completion_time_ms
                    FROM procedural_patterns
                    WHERE tenant_id = :tid AND task_type = :task_type
                    ORDER BY (success_count::float / GREATEST(success_count + failure_count, 1)) DESC,
                             avg_completion_time_ms ASC NULLS LAST
                    LIMIT 1
                """),
                {"tid": str(tenant_id), "task_type": task_type},
            )
            row = result.fetchone()
            if row is None:
                return None
            return {
                "pattern_name": row[0],
                "task_type": row[1],
                "trigger_conditions": row[2],
                "action_sequence": row[3],
                "success_count": row[4],
                "failure_count": row[5],
                "avg_completion_time_ms": row[6],
            }

    async def record_outcome(
        self,
        tenant_id: UUID,
        pattern_name: str,
        success: bool,
        duration_ms: float,
    ) -> None:
        field = "success_count" if success else "failure_count"
        async with get_session(tenant_id) as session:
            await session.execute(
                text(f"""
                    UPDATE procedural_patterns
                    SET {field} = {field} + 1,
                        avg_completion_time_ms = COALESCE(
                            (avg_completion_time_ms * (success_count + failure_count) + :duration)
                            / (success_count + failure_count + 1),
                            :duration
                        ),
                        last_used_at = NOW()
                    WHERE tenant_id = :tid AND pattern_name = :name
                """),
                {
                    "tid": str(tenant_id),
                    "name": pattern_name,
                    "duration": duration_ms,
                },
            )


procedural_memory_store = ProceduralMemoryStore()
