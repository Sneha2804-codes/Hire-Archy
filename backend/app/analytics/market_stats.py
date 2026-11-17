"""Pandas-based job-market summaries and candidate-specific skill ROI."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.analytics.matcher import score_candidate_job


def _record(job: Any) -> dict[str, Any]:
    """Convert a SQLAlchemy Job or dictionary into analytics fields."""
    fields = (
        "title", "company", "location", "country", "work_mode", "salary_min_usd",
        "salary_max_usd", "experience_level", "description", "skills", "category",
        "apply_url", "source", "posted_at", "embedding", "id",
    )
    if isinstance(job, dict):
        return {field: job.get(field) for field in fields}
    return {field: getattr(job, field, None) for field in fields}


def _json_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a Pandas result to JSON-friendly Python primitives."""
    clean = frame.astype(object).where(pd.notna(frame), None)
    return clean.to_dict(orient="records")


def compute_market_stats(
    jobs: list[Any],
    profile: dict[str, Any] | None = None,
    cv_text: str = "",
    cv_embedding: list[float] | None = None,
    top_skills: int = 15,
    semantic_scores: dict[int, float] | None = None,
) -> dict[str, Any]:
    """Aggregate salary, skill demand, job volume, and optional skill-gap ROI.

    Salaries use the midpoint of each published/imputed range. Personal skill
    ROI counts missing skills in jobs scoring at least 60/100, then orders by
    occurrence count and average match score so frequent, reachable skills rank
    first. Estimated salary rows are included in the market distributions.
    """
    records = [_record(job) for job in jobs]
    frame = pd.DataFrame(records)
    if frame.empty:
        frame = pd.DataFrame(columns=[
            "title", "company", "work_mode", "salary_min_usd", "salary_max_usd",
            "experience_level", "skills", "category",
        ])
    for column in ("salary_min_usd", "salary_max_usd"):
        frame[column] = pd.to_numeric(frame.get(column), errors="coerce")
    frame["mean_salary_usd"] = (frame["salary_min_usd"] + frame["salary_max_usd"]) / 2

    skill_rows = []
    for _, job in frame.iterrows():
        skills = job.get("skills")
        if not isinstance(skills, (list, tuple, set)):
            skills = []
        for skill in dict.fromkeys(str(value).strip() for value in skills if str(value).strip()):
            skill_rows.append({"skill": skill, "mean_salary_usd": job["mean_salary_usd"]})
    if skill_rows:
        skills_frame = pd.DataFrame(skill_rows)
        top = (
            skills_frame.groupby("skill", as_index=False)
            .agg(frequency=("skill", "size"), mean_salary_usd=("mean_salary_usd", "mean"))
            .sort_values(["frequency", "skill"], ascending=[False, True])
            .head(top_skills)
        )
        top["mean_salary_usd"] = top["mean_salary_usd"].round(2)
        top_skills_result = _json_records(top)
    else:
        top_skills_result = []

    salaries = frame.dropna(subset=["mean_salary_usd"])
    if not salaries.empty:
        salary_distribution = (
            salaries.groupby(["experience_level", "work_mode"], dropna=False)["mean_salary_usd"]
            .agg(
                count="count",
                minimum="min",
                p25=lambda values: values.quantile(0.25),
                median="median",
                p75=lambda values: values.quantile(0.75),
                maximum="max",
            )
            .reset_index()
            .sort_values(["experience_level", "work_mode"])
        )
        quartile_columns = ["minimum", "p25", "median", "p75", "maximum"]
        salary_distribution[quartile_columns] = salary_distribution[quartile_columns].round(2)
        salary_result = _json_records(salary_distribution)
    else:
        salary_result = []

    if not frame.empty:
        volume = (
            frame.groupby(["category", "work_mode"], dropna=False)
            .size()
            .rename("job_count")
            .reset_index()
            .sort_values(["category", "work_mode"])
        )
        volume_result = _json_records(volume)
    else:
        volume_result = []

    roi_result: list[dict[str, Any]] = []
    if profile is not None:
        candidates: dict[str, list[float]] = {}
        for job in jobs:
            match = score_candidate_job(
                profile,
                cv_text,
                cv_embedding,
                job,
                semantic_similarity=(semantic_scores or {}).get(_record(job).get("id")),
            )
            if match["total_score"] < 60:
                continue
            for skill in match["missing_skills"]:
                candidates.setdefault(skill, []).append(match["total_score"])
        roi_result = [
            {
                "skill": skill,
                "high_scoring_jobs": len(scores),
                "mean_match_score": round(sum(scores) / len(scores), 2),
            }
            for skill, scores in sorted(candidates.items(), key=lambda item: (-len(item[1]), -sum(item[1]) / len(item[1]), item[0]))[:5]
        ]

    return {
        "jobs_analyzed": len(records),
        "median_salary_usd": round(float(frame["mean_salary_usd"].median()), 2) if frame["mean_salary_usd"].notna().any() else None,
        "remote_role_share": round(float((frame["work_mode"] == "remote").mean()), 4) if len(frame) else 0.0,
        "top_skills": top_skills_result,
        "salary_distribution": salary_result,
        "job_volume": volume_result,
        "personal_skill_gap_roi": roi_result,
    }
