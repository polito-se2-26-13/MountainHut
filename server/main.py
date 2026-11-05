# run with: py -m uvicorn server.main:app --reload  (from project root)
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.config.config import ORIGIN
from server.models.error.app_error import AppError
from server.middleware.error_middleware import error_handler
from server.database import Base, engine
import server.models.DAO  # noqa: F401 - registers models with Base.metadata
from server.routes import(
    user_routes,
    res_routes,
    slot_routes,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all tables on startup if they don't exist."""
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

#app.include_router(reservation_router)


@app.get("/api/health")
async def health():
    """Quick check that the backend is running."""
    return {"status": "ok"}

app.include_router(user_routes.router)
app.include_router(res_routes.router)
app.include_router(slot_routes.router)

app.add_exception_handler(AppError, error_handler)
app.add_exception_handler(Exception, error_handler)
