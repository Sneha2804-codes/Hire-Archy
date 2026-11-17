"""Backward-compatible job listing response models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobMatchResponse(BaseModel):
    """Transparent match score and skill comparison for an optional CV."""

    total_score: float
    semantic_score: float
    skill_score: float
    experience_score: float
    tfidf_similarity: float
    skill_jaccard: float
    matched_skills: list[str]
    missing_skills: list[str]


class JobResponse(BaseModel):
    """Existing job fields plus optional engineering and region metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    location: str
    country: str
    region: str | None = None
    engineering_branch: str | None = None
    domain: str | None = None
    is_live: bool = True
    work_mode: str
    salary_min_usd: float
    salary_max_usd: float
    salary_display: str | None = None
    salary_is_estimated: bool
    experience_level: str
    description: str
    skills: list[str]
    category: str
    apply_url: str
    source: str
    posted_at: datetime
    match: JobMatchResponse | None = None


class JobPageResponse(BaseModel):
    """Paginated response used by the existing GET /api/jobs contract."""

    items: list[JobResponse]
    total: int
    page: int
    limit: int


class LiveSearchRequest(BaseModel):
    """Filters accepted by the on-demand live-source search endpoint."""

    q: str | None = None
    region: str | None = None
    engineering_branch: str | None = None
    domain: str | None = None
