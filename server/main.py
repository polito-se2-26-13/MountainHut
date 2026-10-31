# run with: py -m uvicorn server.main:app --reload  (from project root)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.config.config import ORIGIN
from server.models.error.app_error import AppError
from server.middleware.error_middleware import error_handler
#from server.database import Base, engine, SessionLocal
from server.routes import(
    user_routes
)

# create all tables on startup if they don't exist
#Base.metadata.create_all(bind=engine)

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

app.include_router(user_routes.router)


app.add_exception_handler(AppError, error_handler)
app.add_exception_handler(Exception, error_handler)