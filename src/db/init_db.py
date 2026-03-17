"""
Initialize database tables on startup.
This creates all tables from SQLAlchemy ORM models if they don't exist.
"""
import asyncio
from sqlalchemy.exc import ProgrammingError

from src.db.postgres import engine, Base
# Import models so they're registered with Base.metadata
from src.db.models.user import User
from src.db.models.tenant import Tenant
from src.db.models.audit import AuditEvent
from src.db.models.session import UserSession


async def init_db():
    """Create all database tables from ORM models."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables initialized successfully")
    except ProgrammingError as e:
        print(f"⚠️  Database initialization warning: {e}")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(init_db())
