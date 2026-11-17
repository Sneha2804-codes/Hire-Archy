"""End-to-end scraper, cleaner, embedding, and persistence workflow."""

from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Any

from app.etl.cleaner import clean_jobs
from app.etl.embeddings import embed_texts
from app.etl.scraper import collect_jobs

logger = logging.getLogger(__name__)


def _embedding_text(job: dict[str, Any]) -> str:
    """Compose the searchable text passed to the embedding model."""
    skills = ", ".join(job.get("skills") or [])
    return "\n".join((
        f"Title: {job.get('title', '')}",
        f"Company: {job.get('company', '')}",
        f"Category: {job.get('category', '')}",
        f"Experience: {job.get('experience_level', '')}",
        f"Skills: {skills}",
        f"Description: {job.get('description', '')}",
    ))


async def run_pipeline(limit: int = 25) -> dict[str, int]:
    """Fetch, clean, deduplicate, embed, save jobs, and record run statistics."""
    if limit < 1:
        raise ValueError("limit must be at least 1")

    # Keep SQLAlchemy imports local so parsing and cleaner tests can run without
    # connecting to a database or importing the persistence layer.
    from sqlalchemy import select

    from app.db import AsyncSessionLocal
    from app.models import Job, ScrapeRun

    raw_jobs = await collect_jobs(limit)
    cleaned, stats = clean_jobs(raw_jobs)
    rows = cleaned.to_dict(orient="records")
    urls = [row["apply_url"] for row in rows]
    async with AsyncSessionLocal() as session:
        existing = set()
        if urls:
            existing = set((await session.scalars(select(Job.apply_url).where(Job.apply_url.in_(urls)))).all())
    new_rows = [row for row in rows if row["apply_url"] not in existing]
    stats["duplicates_skipped"] += len(rows) - len(new_rows)
    vectors = await embed_texts([_embedding_text(row) for row in new_rows])

    async with AsyncSessionLocal() as session:
        async with session.begin():
            for row, vector in zip(new_rows, vectors):
                row["embedding"] = vector
                row["salary_is_estimated"] = bool(row["salary_is_estimated"])
                if hasattr(row["posted_at"], "to_pydatetime"):
                    row["posted_at"] = row["posted_at"].to_pydatetime()
                session.add(Job(**row))
            session.add(ScrapeRun(
                source="RemoteOK,WeWorkRemotely",
                jobs_fetched=stats["jobs_fetched"],
                duplicates_skipped=stats["duplicates_skipped"],
                invalid_dropped=stats["invalid_dropped"],
            ))

    logger.info(
        "ETL completed: fetched=%d inserted=%d duplicates=%d invalid=%d",
        stats["jobs_fetched"], len(new_rows), stats["duplicates_skipped"], stats["invalid_dropped"],
    )
    stats["inserted"] = len(new_rows)
    return stats


def main() -> None:
    """CLI entry point, e.g. ``python -m app.etl.run --limit 25``."""
    parser = argparse.ArgumentParser(description="Fetch and normalize remote tech jobs")
    parser.add_argument("--limit", type=int, default=25, help="Maximum raw records fetched across sources")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(run_pipeline(args.limit))


if __name__ == "__main__":
    main()
