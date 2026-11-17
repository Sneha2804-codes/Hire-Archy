"""Filtered and optionally candidate-ranked job listing endpoint."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.matcher import _cosine, score_candidate_job
from app.db import get_db
from app.models import CandidateProfile, Job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _payload(job: Job) -> dict:
    """Serialize a Job model into a stable API shape."""
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "country": job.country,
        "work_mode": job.work_mode,
        "salary_min_usd": job.salary_min_usd,
        "salary_max_usd": job.salary_max_usd,
        "salary_is_estimated": job.salary_is_estimated,
        "experience_level": job.experience_level,
        "description": job.description,
        "skills": job.skills,
        "category": job.category,
        "apply_url": job.apply_url,
        "source": job.source,
        "posted_at": job.posted_at,
    }


@router.get("")
async def list_jobs(
    q: str | None = None,
    category: str | None = None,
    work_mode: Literal["remote", "hybrid", "onsite"] | None = None,
    experience_level: list[Literal["entry", "mid", "senior", "lead"]] = Query(default=[]),
    min_salary: float | None = Query(default=None, ge=0),
    skills: list[str] = Query(default=[]),
    profile_id: int | None = Query(default=None, ge=1),
    sort_by: Literal["recent", "salary", "match"] = "recent",
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Filter jobs and return optional composite scores for a candidate."""
    statement = select(Job)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        statement = statement.where(or_(Job.title.ilike(pattern), Job.company.ilike(pattern), Job.description.ilike(pattern)))
    if category:
        statement = statement.where(Job.category == category)
    if work_mode:
        statement = statement.where(Job.work_mode == work_mode)
    if experience_level:
        statement = statement.where(Job.experience_level.in_(experience_level))
    if min_salary is not None:
        statement = statement.where(Job.salary_max_usd >= min_salary)

    profile = None
    if profile_id is not None:
        profile = await session.get(CandidateProfile, profile_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Candidate profile not found")
    if sort_by == "match" and profile is None:
        raise HTTPException(status_code=400, detail="sort_by=match requires profile_id")

    if sort_by == "salary":
        statement = statement.order_by(Job.salary_max_usd.desc(), Job.posted_at.desc())
    elif sort_by == "recent":
        statement = statement.order_by(Job.posted_at.desc(), Job.id.desc())
    jobs = list((await session.scalars(statement)).all())
    if skills:
        requested_skills = {skill.strip().casefold() for skill in skills if skill.strip()}
        jobs = [
            job for job in jobs
            if requested_skills.issubset({str(skill).casefold() for skill in (job.skills or [])})
        ]

    semantic_by_id = {
        job.id: _cosine(profile.embedding, job.embedding)
        for job in jobs
        if profile is not None and profile.embedding and job.embedding
    }
    match_by_id = {}
    if profile is not None:
        extracted = profile.extracted_data or {}
        match_by_id = {
            job.id: score_candidate_job(
                extracted,
                profile.raw_text,
                profile.embedding,
                job,
                semantic_similarity=semantic_by_id.get(job.id),
            )
            for job in jobs
        }
        if sort_by == "match":
            jobs.sort(key=lambda job: (-match_by_id[job.id]["total_score"], job.id))

    total = len(jobs)
    start = (page - 1) * limit
    selected = jobs[start : start + limit]
    items = []
    for job in selected:
        item = _payload(job)
        if profile is not None:
            item["match"] = match_by_id[job.id]
        items.append(item)
    return {"items": items, "total": total, "page": page, "limit": limit}
