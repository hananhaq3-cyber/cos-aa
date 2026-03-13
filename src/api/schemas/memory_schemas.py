"""
Pydantic request/response schemas for memory endpoints.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MemorySearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    tiers: list[str] = Field(
        default=["semantic", "episodic"],
        description="Memory tiers to search",
    )
    tags: list[str] = []


class MemoryFragmentResponse(BaseModel):
    fragment_id: UUID
    tier: str
    content: str
    summary: str = ""
    relevance_score: float = 0.0
    source_type: str = ""
    created_at: datetime | None = None
    tags: list[str] = []


class MemorySearchResponse(BaseModel):
    query: str
    results: list[MemoryFragmentResponse] = []
    total: int = 0
    retrieval_latency_ms: float = 0.0
