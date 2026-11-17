"""CLI entry point for quota-aware live job ingestion."""

from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Any

from app.etl.live_sources import collect_live_jobs
from app.etl.pipeline import embedding_text, ingest_live_records

logger = logging.getLogger(__name__)


def _embedding_text(job: dict[str, Any]) -> str:
    """Backward-compatible alias for the shared live pipeline text builder."""
    return embedding_text(job)


async def run_pipeline(limit: int = 250) -> dict[str, Any]:
    """Collect real listings, normalize and classify them, then persist them."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    raw_jobs = await collect_live_jobs(limit=limit)
    result = await ingest_live_records(raw_jobs, source_label="LiveSync")
    logger.info(
        "Live ETL completed: fetched=%d inserted=%d duplicates=%d invalid=%d",
        result["jobs_fetched"], result["inserted"], result["duplicates_skipped"],
        result["invalid_dropped"],
    )
    return {key: value for key, value in result.items() if key != "items"}


def main() -> None:
    """Run the live sync; Adzuna calls remain capped independently at eight."""
    parser = argparse.ArgumentParser(description="Ingest genuine live engineering and technology roles")
    parser.add_argument("--limit", type=int, default=250, help="Maximum postings returned across sources")
    args = parser.parse_args()
    # httpx logs full request URLs at INFO; Adzuna credentials are query
    # parameters, so suppress those logs to keep secrets out of the console.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    asyncio.run(run_pipeline(args.limit))


if __name__ == "__main__":
    main()
