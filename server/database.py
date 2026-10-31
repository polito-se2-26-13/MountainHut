"""
#sicroMode
#Database connection shared by the whole backend (SQLite file next to this module).
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = f"sqlite:///{Path(__file__).parent / 'mountainHut.sqlite'}"

# check_same_thread=False lets FastAPI use the connection from its worker threads
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    #Parent class of every table defined in models.py.


def get_db():
    #FastAPI dependency: gives each request its own session and closes it at the end.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""
#ASINCRO MODE
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from server.config.config import DATABASE_URL
import importlib
import pkgutil
import server.models.DAO as dao_package

# --- Create the async engine ---
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # set to True if you want SQL logs
    future=True
)

# --- Create the async session maker ---
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
    class_=AsyncSession
)

# --- Declare the Base for ORM models ---
Base = declarative_base()

# --- Dependency function for FastAPI routes ---
async def get_db():
    """FastAPI dependency to get an async database session."""
    async with AsyncSessionLocal() as session:
        yield session

def _import_all_daos():
    """Importa dinamicamente tutti i moduli DAO."""
    package_path = dao_package.__path__
    package_name = dao_package.__name__
    for _, module_name, _ in pkgutil.iter_modules(package_path):
        importlib.import_module(f"{package_name}.{module_name}")

async def init_db():
    _import_all_daos()
    #from app.models.DAO import DAO  # ensure all models imported
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def reset_db():
    """Drop all tables and recreate them (resets database to empty state)."""
    from server.models import DAO  # ensure all models imported
    async with engine.begin() as conn:
        # Drop all tables
        await conn.run_sync(Base.metadata.drop_all)