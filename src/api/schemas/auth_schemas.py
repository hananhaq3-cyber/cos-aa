"""Request and response schemas for authentication endpoints."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_name: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    tenant_id: UUID
    email: str
    role: str
    expires_in: int
    jti: str = ""
    email_verified: bool = False


class SessionResponse(BaseModel):
    id: UUID
    jti: str
    user_agent: str | None = None
    ip_address: str | None = None
    country: str | None = None
    created_at: datetime
    expires_at: datetime
    last_activity_at: datetime | None = None
    is_current: bool = False
    is_revoked: bool = False
