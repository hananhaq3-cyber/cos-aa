"""
Pydantic request/response schemas for memory endpoints.
"""
from __future__ import annotations

from datetime import datetime
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
    event_types: list[str] = Field(default=[], description="Filter by event type")
    created_after: datetime | None = Field(default=None, description="Filter memories created after this date")
    created_before: datetime | None = Field(default=None, description="Filter memories created before this date")
    sort_by: str = Field(default="relevance", description="Sort by: relevance or date")


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


class StoreMemoryRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    event_type: str = Field(default="manual", max_length=64)
    tags: list[str] = []
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)


class MemoryStatsResponse(BaseModel):
    total: int = 0
    by_tier: dict[str, int] = {}


class MemoryListResponse(BaseModel):
    memories: list[MemoryFragmentResponse] = []
    total: int = 0
