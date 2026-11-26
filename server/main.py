# run from the project root, after creating the database:
# py -m server.scripts.db_setup migrate
# py -m uvicorn server.main:app --reload
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.config.config import ORIGIN
from server.models.error.app_error import AppError
from server.middleware.error_middleware import error_handler
from server.routes import(
    auth_routes,
    res_routes,
    slot_routes,
)


# the tables are made by the migrations (db_setup migrate), not at startup
app = FastAPI(title="Mountain Hut")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    """Quick check that the backend is running."""
    return {"status": "ok"}

app.include_router(auth_routes.router)
app.include_router(res_routes.router)
app.include_router(slot_routes.router)

app.add_exception_handler(AppError, error_handler)
app.add_exception_handler(Exception, error_handler)
