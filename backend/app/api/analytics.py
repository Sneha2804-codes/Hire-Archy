"""Labor-market analytics endpoint."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.matcher import _cosine
from app.analytics.market_stats import compute_market_stats
from app.db import get_db
from app.models import CandidateProfile, Job

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
async def analytics_overview(
    profile_id: int | None = Query(default=None, ge=1),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Return market aggregates and optional candidate skill-gap ROI."""
    jobs = list((await session.scalars(select(Job))).all())
    profile = None
    cv_text = ""
    cv_embedding = None
    if profile_id is not None:
        profile_record = await session.get(CandidateProfile, profile_id)
        if profile_record is None:
            raise HTTPException(status_code=404, detail="Candidate profile not found")
        profile = profile_record.extracted_data or {}
        cv_text = profile_record.raw_text
        cv_embedding = profile_record.embedding
    semantic_scores = None
    if profile is not None and cv_embedding:
        semantic_scores = {
            job.id: _cosine(cv_embedding, job.embedding)
            for job in jobs
            if job.embedding
        }
    return compute_market_stats(jobs, profile, cv_text, cv_embedding, semantic_scores=semantic_scores)
