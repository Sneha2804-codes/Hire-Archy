"""HTTP endpoints for starting and inspecting ingestion runs."""

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.etl.run import run_pipeline
from app.models import ScrapeRun

router = APIRouter(prefix="/api/etl", tags=["etl"])


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
async def start_etl(
    background_tasks: BackgroundTasks,
    limit: int = Query(default=25, ge=1, le=500),
) -> dict[str, int | str]:
    """Schedule a background collection run and return immediately."""
    background_tasks.add_task(run_pipeline, limit)
    return {"status": "scheduled", "limit": limit}


@router.get("/logs")
async def get_etl_logs(
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, int | str | datetime]]:
    """Return recent persisted ETL counters, newest first."""
    runs = (await session.scalars(
        select(ScrapeRun).order_by(ScrapeRun.run_at.desc(), ScrapeRun.id.desc()).limit(limit)
    )).all()
    return [
        {
            "id": run.id,
            "source": run.source,
            "jobs_fetched": run.jobs_fetched,
            "duplicates_skipped": run.duplicates_skipped,
            "invalid_dropped": run.invalid_dropped,
            "run_at": run.run_at,
        }
        for run in runs
    ]
