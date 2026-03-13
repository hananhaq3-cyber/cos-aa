"""
Admin router: API key management and quota monitoring.
GET    /api/v1/admin/keys
POST   /api/v1/admin/keys
DELETE /api/v1/admin/keys/{key_id}
GET    /api/v1/admin/quotas
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.auth.oauth2 import get_current_user
from src.api.auth.rbac import require_permission
from src.api.schemas.admin_schemas import (
    ApiKeyListResponse,
    ApiKeyResponse,
    GenerateApiKeyResponse,
    QuotaItem,
    QuotaListResponse,
    RevokeApiKeyResponse,
)
from src.auth.tenant import encrypt_api_key

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/keys", response_model=ApiKeyListResponse)
async def list_api_keys(
    request: Request,
    user: dict = Depends(require_permission("admin:keys")),
) -> ApiKeyListResponse:
    """List all API keys for the tenant (masked)."""
    tenant_id: UUID = request.state.tenant_id

    # In production this would query the DB; placeholder for now
    return ApiKeyListResponse(keys=[])


@router.post("/keys", response_model=GenerateApiKeyResponse)
async def generate_api_key(
    request: Request,
    user: dict = Depends(require_permission("admin:keys")),
) -> GenerateApiKeyResponse:
    """Generate a new AES-256-GCM encrypted API key for the tenant."""
    tenant_id: UUID = request.state.tenant_id

    raw_key = f"cos-aa_{secrets.token_hex(32)}"
    encrypted = encrypt_api_key(raw_key)

    key_id = uuid4()
    now = datetime.now(timezone.utc)

    # In production, persist (key_id, tenant_id, encrypted, created_at) to DB

    return GenerateApiKeyResponse(
        key_id=key_id,
        raw_key=raw_key,
        created_at=now,
    )


@router.delete("/keys/{key_id}", response_model=RevokeApiKeyResponse)
async def revoke_api_key(
    key_id: UUID,
    request: Request,
    user: dict = Depends(require_permission("admin:keys")),
) -> RevokeApiKeyResponse:
    """Revoke an existing API key."""
    tenant_id: UUID = request.state.tenant_id

    # In production, mark as revoked in DB
    return RevokeApiKeyResponse(key_id=key_id, revoked=True)


@router.get("/quotas", response_model=QuotaListResponse)
async def get_quotas(
    request: Request,
    user: dict = Depends(get_current_user),
) -> QuotaListResponse:
    """Get current usage quotas for the tenant."""
    tenant_id: UUID = request.state.tenant_id

    # In production, query actual usage metrics from DB/Redis
    quotas = [
        QuotaItem(resource="OODA Cycles / day", used=0, limit=5000),
        QuotaItem(resource="LLM Tokens / day", used=0, limit=5_000_000),
        QuotaItem(resource="Memory Fragments", used=0, limit=100_000),
        QuotaItem(resource="Agent Spawns / month", used=0, limit=50),
        QuotaItem(resource="API Requests / hour", used=0, limit=1000),
        QuotaItem(resource="Storage (MB)", used=0, limit=1024),
    ]

    return QuotaListResponse(quotas=quotas)
