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


# Raw ALTER TABLE statements using IF NOT EXISTS (PostgreSQL 9.6+)
_ALTER_STATEMENTS = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR(32)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider_id VARCHAR(256)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ",
    "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS goal TEXT",
]


async def init_db():
    """Create all database tables from ORM models and apply missing columns."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Tables created/verified")

            # Add missing columns to existing tables
            for stmt in _ALTER_STATEMENTS:
                try:
                    await conn.execute(text(stmt))
                except Exception as e:
                    print(f"  ⚠️  ALTER: {e}")
            print("✅ Missing columns applied")

        print("✅ Database initialized successfully")
    except ProgrammingError as e:
        print(f"⚠️  Database initialization warning: {e}")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(init_db())
