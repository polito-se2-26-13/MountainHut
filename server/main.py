# run with: py -m uvicorn server.main:app --reload  (from project root)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.config.config import ORIGIN
from server.database import Base, engine, SessionLocal
import server.models.DAO  # noqa: F401 - registers models with Base.metadata

# create all tables on startup if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mountain Hut")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGIN,
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """Quick check that the backend is running."""
    return {"status": "ok"}
