"""Shared live-ingestion pipeline for scheduled syncs and on-demand searches."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from app.etl.cleaner import clean_jobs, normalize_company, normalize_title
from app.etl.embeddings import embed_texts


def embedding_text(job: dict[str, Any]) -> str:
    """Compose role, geography, taxonomy, skills, and body for matching vectors."""
    return "\n".join((
        f"Title: {job.get('title', '')}",
        f"Company: {job.get('company', '')}",
        f"Branch: {job.get('engineering_branch', '')}",
        f"Domain: {job.get('domain', '')}",
        f"Region: {job.get('region', '')}; Country: {job.get('country', '')}",
        f"Category: {job.get('category', '')}",
        f"Experience: {job.get('experience_level', '')}",
        f"Skills: {', '.join(job.get('skills') or [])}",
        f"Description: {job.get('description', '')}",
    ))


async def ingest_live_records(
    raw_jobs: list[dict[str, Any]],
    source_label: str = "LiveSources",
    filters: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    """Clean, country-aware deduplicate, embed, persist, and return inserted jobs."""
    from sqlalchemy import select

    from app.db import AsyncSessionLocal, initialize_database
    from app.models import Job, ScrapeRun

    await initialize_database()
    cleaned, stats = clean_jobs(raw_jobs)
    rows = cleaned.to_dict(orient="records")
    filters = filters or {}
    filtered_rows = []
    for row in rows:
        searchable = " ".join((row["title"], row["company"], row["description"], " ".join(row["skills"]))).casefold()
        if filters.get("q") and filters["q"].casefold() not in searchable:
            continue
        if filters.get("region") and row["region"] != filters["region"]:
            continue
        if filters.get("engineering_branch") and row["engineering_branch"] != filters["engineering_branch"]:
            continue
        if filters.get("domain") and row["domain"] != filters["domain"]:
            continue
        filtered_rows.append(row)
    stats["invalid_dropped"] += len(rows) - len(filtered_rows)
    rows = filtered_rows

    async with AsyncSessionLocal() as session:
        existing_jobs = (await session.execute(select(Job.title, Job.company, Job.country, Job.apply_url))).all()
    existing_keys = {
        (normalize_title(title), normalize_company(company), (country or "").casefold())
        for title, company, country, _ in existing_jobs
    }
    existing_urls = {url for _, _, _, url in existing_jobs}
    unique_rows: list[dict[str, Any]] = []
    seen_keys: list[tuple[str, str, str]] = []
    seen_urls = set(existing_urls)
    duplicates = 0
    for row in rows:
        key = (normalize_title(row["title"]), normalize_company(row["company"]), str(row["country"]).casefold())
        if row["apply_url"] in seen_urls or key in existing_keys or key in seen_keys:
            duplicates += 1
            continue
        # Fuzzy comparison remains country scoped, so identical titles in other
        # markets remain distinct opportunities.
        title_company = (key[0], key[1])
        if any(
            key[2] == prior[2]
            and SequenceMatcher(None, title_company[0], prior[0]).ratio() >= 0.93
            and SequenceMatcher(None, title_company[1], prior[1]).ratio() >= 0.93
            for prior in seen_keys
        ):
            duplicates += 1
            continue
        unique_rows.append(row)
        seen_keys.append(key)
        seen_urls.add(row["apply_url"])

    stats["duplicates_skipped"] += duplicates
    vectors = await embed_texts([embedding_text(row) for row in unique_rows])
    inserted: list[Job] = []
    async with AsyncSessionLocal() as session:
        async with session.begin():
            for row, vector in zip(unique_rows, vectors):
                row["embedding"] = vector
                row["salary_is_estimated"] = bool(row["salary_is_estimated"])
                row["is_live"] = bool(row.get("is_live", True))
                if hasattr(row["posted_at"], "to_pydatetime"):
                    row["posted_at"] = row["posted_at"].to_pydatetime()
                job = Job(**row)
                session.add(job)
                inserted.append(job)
            session.add(ScrapeRun(
                source=source_label[:100],
                jobs_fetched=stats["jobs_fetched"],
                duplicates_skipped=stats["duplicates_skipped"],
                invalid_dropped=stats["invalid_dropped"],
            ))
            await session.flush()

    stats["inserted"] = len(inserted)
    stats["items"] = inserted
    return stats
