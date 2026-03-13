"""
Pydantic request/response schemas for admin endpoints.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ApiKeyResponse(BaseModel):
    key_id: UUID
    masked_key: str
    created_at: datetime


class ApiKeyListResponse(BaseModel):
    keys: list[ApiKeyResponse] = []


class GenerateApiKeyResponse(BaseModel):
    key_id: UUID
    raw_key: str  # Only returned once at generation time
    created_at: datetime


class RevokeApiKeyResponse(BaseModel):
    key_id: UUID
    revoked: bool


class QuotaItem(BaseModel):
    resource: str
    used: int
    limit: int


class QuotaListResponse(BaseModel):
    quotas: list[QuotaItem] = []
