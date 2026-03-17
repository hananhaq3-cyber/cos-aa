"""
Memory router: CRUD + search across memory tiers.
"""
from __future__ import annotations

import time
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text

from src.api.auth.oauth2 import get_current_user
from src.api.schemas.memory_schemas import (
    MemoryFragmentResponse,
    MemoryListResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryStatsResponse,
    StoreMemoryRequest,
)
from src.db.postgres import async_session_factory
from src.memory.episodic_memory import episodic_memory_store
from src.memory.memory_service import memory_service

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


@router.post("/search", response_model=MemorySearchResponse)
async def search_memory(
    body: MemorySearchRequest,
    request: Request,
    user: dict = Depends(get_current_user),
) -> MemorySearchResponse:
    """Search across memory tiers using hybrid retrieval with optional filters."""
    tenant_id: UUID = request.state.tenant_id
    start = time.perf_counter()

    results = await memory_service.retrieve_context(
        tenant_id=tenant_id,
        query=body.query,
        top_k=body.top_k,
    )

    # results is list[MemoryFragment] (domain objects from retrieval_ranker)
    fragments: list[MemoryFragmentResponse] = []
    for item in results:
        tier_name = item.tier.value if hasattr(item.tier, "value") else str(item.tier)
        # Filter by requested tiers
        if tier_name.lower() not in [t.lower() for t in body.tiers]:
            continue

        # Filter by event types if specified
        source_type = item.source_type.value if hasattr(item.source_type, "value") else str(item.source_type)
        if body.event_types and source_type.lower() not in [t.lower() for t in body.event_types]:
            continue

        # Filter by date range if specified
        if item.created_at:
            if body.created_after and item.created_at < body.created_after:
                continue
            if body.created_before and item.created_at > body.created_before:
                continue

        # Filter by tags if specified
        if body.tags and not any(tag.lower() in [t.lower() for t in item.tags or []] for tag in body.tags):
            continue

        fragments.append(
            MemoryFragmentResponse(
                fragment_id=uuid4(),
                tier=tier_name,
                content=item.content,
                summary=item.summary or "",
                relevance_score=item.relevance_score,
                source_type=source_type,
                tags=item.tags or [],
                created_at=item.created_at,
            )
        )

    # Sort results
    if body.sort_by == "date" and fragments:
        fragments.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
    elif body.sort_by == "relevance":
        fragments.sort(key=lambda x: x.relevance_score, reverse=True)

    elapsed = (time.perf_counter() - start) * 1000
    return MemorySearchResponse(
        query=body.query,
        results=fragments,
        total=len(fragments),
        retrieval_latency_ms=round(elapsed, 2),
    )


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    request: Request,
    user: dict = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
    event_type: str | None = None,
) -> MemoryListResponse:
    """List recent memories with optional filters."""
    tenant_id: UUID = request.state.tenant_id

    memories = await episodic_memory_store.query_recent(
        tenant_id=tenant_id,
        limit=limit,
        event_type=event_type,
    )

    fragments = [
        MemoryFragmentResponse(
            fragment_id=UUID(m["id"]) if "id" in m else uuid4(),
            tier=m.get("event_type", "EPISODIC"),
            content=str(m.get("content", "")),
            relevance_score=m.get("importance_score", 0.0),
            source_type="EPISODIC",
            created_at=m.get("created_at"),
            tags=m.get("tags") or [],
        )
        for m in memories
    ]

    return MemoryListResponse(memories=fragments, total=len(fragments))


@router.post("", response_model=MemoryFragmentResponse)
async def store_memory(
    body: StoreMemoryRequest,
    request: Request,
    user: dict = Depends(get_current_user),
) -> MemoryFragmentResponse:
    """Store a new manual memory fragment."""
    tenant_id: UUID = request.state.tenant_id

    memory_id = await episodic_memory_store.write_event(
        tenant_id=tenant_id,
        session_id=uuid4(),  # Manual memories get a placeholder session
        agent_id=uuid4(),    # Placeholder agent
        event_type=body.event_type,
        content={"text": body.content},
        importance_score=body.importance_score,
        tags=body.tags,
    )

    return MemoryFragmentResponse(
        fragment_id=memory_id,
        tier=body.event_type,
        content=body.content,
        relevance_score=body.importance_score,
        source_type="manual",
        tags=body.tags,
    )


@router.delete("/{fragment_id}")
async def delete_memory(
    fragment_id: UUID,
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict:
    """Delete a memory fragment by ID."""
    tenant_id: UUID = request.state.tenant_id

    async with async_session_factory() as session:
        await session.execute(
            text("SET app.tenant_id = :tid"), {"tid": str(tenant_id)}
        )
        result = await session.execute(
            text(
                "DELETE FROM episodic_memories "
                "WHERE id = :id AND tenant_id = :tid"
            ),
            {"id": str(fragment_id), "tid": str(tenant_id)},
        )
        await session.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {"message": "Memory deleted"}


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(
    request: Request,
    user: dict = Depends(get_current_user),
) -> MemoryStatsResponse:
    """Get memory counts grouped by event type."""
    tenant_id: UUID = request.state.tenant_id

    async with async_session_factory() as session:
        await session.execute(
            text("SET app.tenant_id = :tid"), {"tid": str(tenant_id)}
        )
        result = await session.execute(
            text(
                "SELECT event_type, COUNT(*) FROM episodic_memories "
                "WHERE tenant_id = :tid GROUP BY event_type"
            ),
            {"tid": str(tenant_id)},
        )
        rows = result.fetchall()

    by_tier: dict[str, int] = {}
    total = 0
    for row in rows:
        by_tier[str(row[0])] = int(row[1])
        total += int(row[1])

    return MemoryStatsResponse(total=total, by_tier=by_tier)


# ── Export ──


@router.get("/export", response_model=dict)
async def export_memory(
    request: Request,
    user: dict = Depends(get_current_user),
    format: str = "json",
) -> dict:
    """Export all memory fragments in JSON or CSV format."""
    tenant_id: UUID = request.state.tenant_id
    import csv
    import json
    from io import StringIO

    async with async_session_factory() as session:
        await session.execute(
            text("SET app.tenant_id = :tid"), {"tid": str(tenant_id)}
        )
        result = await session.execute(
            text(
                "SELECT id, event_type, content, metadata, created_at FROM episodic_memories WHERE tenant_id = :tid ORDER BY created_at DESC"
            ),
            {"tid": str(tenant_id)},
        )
        memories = result.fetchall()

    if not memories:
        return {"data": "", "filename": f"memory-export.{format}"}

    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Type", "Content", "Created"])
        for mem in memories:
            writer.writerow([str(mem[0]), mem[1], mem[2], str(mem[4])])
        return {"data": output.getvalue(), "filename": "memory-export.csv"}

    else:  # json
        json_data = [
            {
                "id": str(mem[0]),
                "type": mem[1],
                "content": mem[2],
                "metadata": json.loads(mem[3]) if mem[3] else {},
                "created_at": str(mem[4]),
            }
            for mem in memories
        ]
        return {"data": json.dumps(json_data, indent=2), "filename": "memory-export.json"}
