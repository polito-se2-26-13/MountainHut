"""Database connection shared by the whole backend (SQLite file next to this module)."""
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = f"sqlite:///{Path(__file__).parent / 'mountainHut.sqlite'}"

# check_same_thread=False lets FastAPI use the connection from its worker threads
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints in SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Base(DeclarativeBase):
    """Parent class of every table defined in models.py."""


def get_db():
    """FastAPI dependency: gives each request its own session and closes it at the end."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all registered tables."""
    # Import all models to ensure they are registered with Base
    import server.models.DAO  # noqa: F401
    Base.metadata.create_all(bind=engine)


def drop_db():
    """Drop all tables."""
    import server.models.DAO  # noqa: F401
    Base.metadata.drop_all(bind=engine)


def reset_db():
    """Drop and recreate all tables."""
    drop_db()
    init_db()
