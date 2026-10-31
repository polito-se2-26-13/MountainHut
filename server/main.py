# run with: py -m uvicorn server.main:app --reload  (from project root)
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.config.config import ORIGIN
from server.database import Base, engine
import server.models.DAO  # noqa: F401 - registers models with Base.metadata
from server.routes import reservation_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async startup and shutdown lifespan context."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Mountain Hut", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGIN,
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reservation_router)


@app.get("/api/health")
async def health():
    """Quick check that the backend is running."""
    return {"status": "ok"}
