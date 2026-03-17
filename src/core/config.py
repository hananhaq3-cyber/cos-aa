"""
Application-wide configuration. Loaded from environment variables via pydantic-settings.
Import `settings` from this module everywhere.
"""
from typing import Literal
import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # --- Application ---
    app_env: Literal["development", "staging", "production"] = "development"
    app_secret_key: str = "dev-secret-change-in-production"
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"
    cors_domain: str = "<YOUR_DOMAIN>"

    # --- PostgreSQL ---
    postgres_url: str = "postgresql+asyncpg://cos_user:cos_pass@localhost:5432/cos_aa"
    postgres_pool_size: int = 20
    postgres_max_overflow: int = 10

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50

    # --- LLM ---
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_provider: Literal["openai", "anthropic"] = "openai"
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    # --- Vector DB ---
    vector_backend: Literal["chroma", "pinecone"] = "chroma"
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    pinecone_api_key: str = ""
    pinecone_environment: str = "us-east-1"

    # --- Auth ---
    jwt_secret_key: str = "dev-jwt-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # --- OAuth ---
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    apple_client_id: str = ""
    apple_client_secret: str = ""
    apple_team_id: str = ""
    apple_key_id: str = ""
    oauth_redirect_base_url: str = "http://localhost:5173"

    # --- Email (Resend) ---
    resend_api_key: str = ""
    email_from: str = "COS-AA <onboarding@resend.dev>"
    frontend_url: str = "https://cos-aa.vercel.app"

    # --- Vault ---
    vault_addr: str = ""
    vault_role: str = ""

    # --- Celery ---
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # --- Observability ---
    otlp_endpoint: str = "http://localhost:4317"
    prometheus_port: int = 9090

    # --- Self-Evolving Agents ---
    spawn_threshold: int = 3
    spawn_window_seconds: int = 86400
    container_registry: str = "ghcr.io/<GITHUB_ORG>/cos-aa"

    # --- OODA ---
    default_max_ooda_iterations: int = 5
    default_ooda_cycle_timeout_seconds: int = 120
    default_human_confirmation_timeout_seconds: int = 60
    cot_confidence_threshold: float = 0.6

    # --- Encryption ---
    encryption_key_version: int = 1

    # --- Sandbox ---
    sandbox_backend: Literal["subprocess", "docker", "gvisor"] = "subprocess"

    def __init__(self, **kwargs):
        # Railway compatibility: Convert DATABASE_URL to asyncpg format
        if not kwargs.get("postgres_url"):
            db_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or "postgresql+asyncpg://cos_user:cos_pass@localhost:5432/cos_aa"
            # Convert postgres:// to postgresql+asyncpg:// for async driver
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            kwargs["postgres_url"] = db_url
        if not kwargs.get("redis_url"):
            kwargs["redis_url"] = os.getenv("REDIS_URL") or "redis://localhost:6379/0"
        super().__init__(**kwargs)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
