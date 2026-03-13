"""
Agent Registry: CRUD operations for agent type definitions and instance tracking.
Manages the routing table cache in Redis for fast agent lookups.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text

from src.core.domain_objects import (
    AgentDefinition,
    AgentDefinitionStatus,
    AgentType,
)
from src.db.postgres import async_session_factory
from src.db.redis_client import redis_client


REGISTRY_CACHE_TTL = 300  # 5 minutes


class AgentRegistry:
    """Manages agent type definitions and instance lifecycle."""

    async def register_type(self, definition: AgentDefinition) -> UUID:
        """Register a new agent type definition in PostgreSQL."""
        async with async_session_factory() as session:
            await session.execute(
                text("""
                    INSERT INTO agent_types (
                        id, tenant_id, type_name, purpose,
                        system_prompt, model_override, status,
                        config, created_at
                    ) VALUES (
                        :id, :tenant_id, :type_name, :purpose,
                        :system_prompt, :model_override, :status,
                        :config, NOW()
                    )
                    ON CONFLICT (tenant_id, type_name) DO UPDATE SET
                        purpose = EXCLUDED.purpose,
                        system_prompt = EXCLUDED.system_prompt,
                        model_override = EXCLUDED.model_override,
                        status = EXCLUDED.status,
                        config = EXCLUDED.config
                """),
                {
                    "id": str(definition.definition_id),
                    "tenant_id": str(definition.tenant_id),
                    "type_name": definition.agent_type_name,
                    "purpose": definition.purpose,
                    "system_prompt": definition.system_prompt,
                    "model_override": definition.model_override or "",
                    "status": definition.status.value,
                    "config": "{}",
                },
            )
            await session.commit()

        # Invalidate routing cache
        await self._invalidate_cache(definition.tenant_id)
        return definition.definition_id

    async def get_type(
        self, tenant_id: UUID, type_name: str
    ) -> AgentDefinition | None:
        """Look up an agent type definition."""
        async with async_session_factory() as session:
            result = await session.execute(
                text("""
                    SELECT id, tenant_id, type_name, purpose,
                           system_prompt, model_override, status, config
                    FROM agent_types
                    WHERE tenant_id = :tid AND type_name = :name
                """),
                {"tid": str(tenant_id), "name": type_name},
            )
            row = result.fetchone()
            if not row:
                return None

            return AgentDefinition(
                definition_id=UUID(row[0]),
                tenant_id=UUID(row[1]),
                agent_type_name=row[2],
                purpose=row[3],
                system_prompt=row[4],
                model_override=row[5] or None,
                status=AgentDefinitionStatus(row[6]),
            )

    async def list_types(
        self, tenant_id: UUID, status: str | None = None
    ) -> list[AgentDefinition]:
        """List all agent type definitions for a tenant."""
        query = "SELECT id, tenant_id, type_name, purpose, system_prompt, model_override, status FROM agent_types WHERE tenant_id = :tid"
        params: dict[str, Any] = {"tid": str(tenant_id)}

        if status:
            query += " AND status = :status"
            params["status"] = status

        query += " ORDER BY created_at DESC"

        async with async_session_factory() as session:
            result = await session.execute(text(query), params)
            rows = result.fetchall()

        return [
            AgentDefinition(
                definition_id=UUID(r[0]),
                tenant_id=UUID(r[1]),
                agent_type_name=r[2],
                purpose=r[3],
                system_prompt=r[4],
                model_override=r[5] or None,
                status=AgentDefinitionStatus(r[6]),
            )
            for r in rows
        ]

    async def update_status(
        self, tenant_id: UUID, definition_id: UUID, new_status: AgentDefinitionStatus
    ) -> None:
        """Update the status of an agent definition."""
        async with async_session_factory() as session:
            await session.execute(
                text("""
                    UPDATE agent_types SET status = :status
                    WHERE id = :id AND tenant_id = :tid
                """),
                {
                    "id": str(definition_id),
                    "tid": str(tenant_id),
                    "status": new_status.value,
                },
            )
            await session.commit()
        await self._invalidate_cache(tenant_id)

    async def register_instance(
        self, tenant_id: UUID, agent_type_name: str, instance_id: str
    ) -> None:
        """Register a running agent instance."""
        key = f"tenant:{tenant_id}:agent_instances:{agent_type_name}"
        await redis_client.client.sadd(key, instance_id)
        await redis_client.client.expire(key, 600)

    async def deregister_instance(
        self, tenant_id: UUID, agent_type_name: str, instance_id: str
    ) -> None:
        key = f"tenant:{tenant_id}:agent_instances:{agent_type_name}"
        await redis_client.client.srem(key, instance_id)

    async def get_instances(
        self, tenant_id: UUID, agent_type_name: str
    ) -> list[str]:
        key = f"tenant:{tenant_id}:agent_instances:{agent_type_name}"
        members = await redis_client.client.smembers(key)
        return [m.decode() if isinstance(m, bytes) else m for m in members]

    async def _invalidate_cache(self, tenant_id: UUID) -> None:
        cache_key = f"tenant:{tenant_id}:agent_routing_cache"
        await redis_client.client.delete(cache_key)


agent_registry = AgentRegistry()
