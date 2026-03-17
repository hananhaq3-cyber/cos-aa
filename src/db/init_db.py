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


# Columns that may be missing from existing tables (migration 005-008)
_MISSING_COLUMNS = [
    # migration 005: OAuth columns on users
    ("users", "oauth_provider", "VARCHAR(32)", None),
    ("users", "oauth_provider_id", "VARCHAR(256)", None),
    # migration 007: email verification columns on users
    ("users", "email_verified", "BOOLEAN NOT NULL", "'false'"),
    ("users", "email_verified_at", "TIMESTAMPTZ", None),
    # migration 008: goal column on sessions
    ("sessions", "goal", "TEXT", None),
]


async def _add_missing_columns(conn):
    """Add columns that create_all cannot add to existing tables."""
    for table, column, col_type, default in _MISSING_COLUMNS:
        try:
            check = await conn.execute(text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :tbl AND column_name = :col"
            ), {"tbl": table, "col": column})
            if check.fetchone() is None:
                ddl = f'ALTER TABLE {table} ADD COLUMN {column} {col_type}'
                if default:
                    ddl += f' DEFAULT {default}'
                await conn.execute(text(ddl))
                print(f"  ✅ Added column {table}.{column}")
        except Exception as e:
            print(f"  ⚠️  Column {table}.{column}: {e}")


async def init_db():
    """Create all database tables from ORM models and apply missing columns."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await _add_missing_columns(conn)
        print("✅ Database tables initialized successfully")
    except ProgrammingError as e:
        print(f"⚠️  Database initialization warning: {e}")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(init_db())
