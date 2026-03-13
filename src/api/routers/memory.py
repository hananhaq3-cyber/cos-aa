"""
Memory router: search across memory tiers.
GET /api/v1/memory/search
"""
from __future__ import annotations

import time
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request

from src.api.auth.oauth2 import get_current_user
from src.api.schemas.memory_schemas import (
    MemoryFragmentResponse,
    MemorySearchRequest,
    MemorySearchResponse,
)
from src.memory.memory_service import memory_service

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


@router.post("/search", response_model=MemorySearchResponse)
async def search_memory(
    body: MemorySearchRequest,
    request: Request,
    user: dict = Depends(get_current_user),
) -> MemorySearchResponse:
    """Search across memory tiers using hybrid retrieval."""
    tenant_id: UUID = request.state.tenant_id
    start = time.perf_counter()

    results = await memory_service.retrieve_context(
        tenant_id=str(tenant_id),
        session_id="",
        query=body.query,
        top_k=body.top_k,
    )

    fragments: list[MemoryFragmentResponse] = []

    # Semantic results
    if "semantic" in body.tiers:
        for item in results.get("semantic", []):
            fragments.append(
                MemoryFragmentResponse(
                    fragment_id=uuid4(),
                    tier="SEMANTIC",
                    content=item.get("content", ""),
                    summary=item.get("summary", ""),
                    relevance_score=item.get("relevance_score", 0.0),
                    source_type=item.get("source_type", ""),
                    tags=item.get("tags", []),
                )
            )

    # Episodic results
    if "episodic" in body.tiers:
        for item in results.get("episodic", []):
            fragments.append(
                MemoryFragmentResponse(
                    fragment_id=uuid4(),
                    tier="EPISODIC",
                    content=str(item.get("content", "")),
                    relevance_score=item.get("importance_score", 0.0),
                    source_type="EPISODIC",
                    tags=item.get("tags", []),
                )
            )

    elapsed = (time.perf_counter() - start) * 1000
    return MemorySearchResponse(
        query=body.query,
        results=fragments,
        total=len(fragments),
        retrieval_latency_ms=round(elapsed, 2),
    )
