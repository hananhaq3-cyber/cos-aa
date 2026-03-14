"""Request and response schemas for authentication endpoints."""
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_max_length(cls, v: str) -> str:
        """Bcrypt limit: passwords must be <= 72 bytes."""
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 bytes or shorter")
        return v


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_name: str

    @field_validator("password")
    @classmethod
    def password_max_length(cls, v: str) -> str:
        """Bcrypt limit: passwords must be <= 72 bytes."""
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must be 72 bytes or shorter")
        return v


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    tenant_id: UUID
    email: str
    role: str
    expires_in: int
