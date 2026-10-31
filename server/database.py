"""Database connection shared by the whole backend (Async SQLite with aiosqlite)."""
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

DB_PATH = Path(__file__).parent / "mountainHut.sqlite"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

# Async engine with SQLite pragma support
engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# For backward compatibility with scripts
SessionLocal = AsyncSessionLocal


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints in SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Base(DeclarativeBase):
    """Parent class of every table defined in models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI async dependency: yields an AsyncSession and closes it at end of request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all registered tables asynchronously."""
    import server.models.DAO  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """Drop all tables asynchronously."""
    import server.models.DAO  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def reset_db():
    """Drop and recreate all tables."""
    await drop_db()
    await init_db()
