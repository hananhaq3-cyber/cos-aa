"""
Initialize database tables on startup.
This creates all tables from SQLAlchemy ORM models if they don't exist,
and adds missing columns from recent migrations.
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from src.db.postgres import engine, Base
# Import models so they're registered with Base.metadata
from src.db.models.user import User
from src.db.models.tenant import Tenant
from src.db.models.audit import AuditEvent
from src.db.models.session import UserSession


async def init_db():
    """Create all database tables from ORM models and apply missing columns."""
    # Step 1: Create tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Tables created/verified")
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        raise

    # Step 2: Add missing columns in a SEPARATE transaction
    alter_statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR(32)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider_id VARCHAR(256)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT false",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ",
        "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS goal TEXT",
    ]
    try:
        async with engine.begin() as conn:
            for stmt in alter_statements:
                print(f"  Running: {stmt[:60]}...")
                await conn.execute(text(stmt))
        print("✅ Missing columns applied")
    except Exception as e:
        print(f"❌ Column migration failed: {e}")
        # Don't raise - allow app to start even if ALTER fails

    print("✅ Database initialized successfully")


if __name__ == "__main__":
    asyncio.run(init_db())
