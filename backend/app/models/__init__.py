"""SQLAlchemy models exported for Alembic metadata discovery."""

from app.models.base import Base
from app.models.candidate_profile import CandidateProfile
from app.models.job import Job
from app.models.scrape_run import ScrapeRun

__all__ = ["Base", "CandidateProfile", "Job", "ScrapeRun"]
