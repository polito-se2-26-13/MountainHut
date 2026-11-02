"""Shared setup of the integration tests: the real API, from the routes down to SQLite,
working on an empty database file created for each test instead of server/mountainHut.sqlite."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from server.database import AsyncSessionLocal, Base, engine
from server.main import app


@pytest.fixture
def db(tmp_path):
    """Session on a new empty database, used by the test to add and check rows."""
    path = tmp_path / "test.db"
    sync_engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(bind=sync_engine)
    # the routes and the repository open their sessions from AsyncSessionLocal, so they use the test database now
    # NullPool because TestClient gives each request its own event loop, and a connection cannot change loop
    AsyncSessionLocal.configure(bind=create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool))
    session = Session(sync_engine)
    yield session
    session.close()
    AsyncSessionLocal.configure(bind=engine)
    sync_engine.dispose()


@pytest.fixture
def client(db):
    """Calls the API like the frontend does, on the same test database."""
    return TestClient(app)
