"""Tenant ORM model — maps to the ``tenants`` table from migration 001."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.postgres import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(64), server_default="shared")
    require_agent_approval: Mapped[bool] = mapped_column(
        Boolean, server_default="true"
    )
    llm_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    quotas: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")

    users = relationship("User", back_populates="tenant")
