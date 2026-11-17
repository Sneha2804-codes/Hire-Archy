"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analytics import router as analytics_router
from app.api.cv import router as cv_router
from app.api.etl import router as etl_router
from app.api.jobs import router as jobs_router
from app.api.taxonomy import router as taxonomy_router
from app.db import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize the local SQLite schema when the API starts."""
    await initialize_database()
    yield


app = FastAPI(title="Hire-Archy API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(etl_router)
app.include_router(cv_router)
app.include_router(jobs_router)
app.include_router(analytics_router)
app.include_router(taxonomy_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}
