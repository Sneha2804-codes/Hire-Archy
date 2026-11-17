"""Job listing model."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Job(Base):
    """A normalized job listing with optional semantic embedding."""

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("work_mode IN ('remote', 'hybrid', 'onsite')", name="ck_jobs_work_mode"),
        CheckConstraint("experience_level IN ('entry', 'mid', 'senior', 'lead')", name="ck_jobs_experience_level"),
        CheckConstraint(
            "category IN ('Software Engineering', 'Data Science', 'AI/ML', 'DevOps', 'Product')",
            name="ck_jobs_category",
        ),
        CheckConstraint("salary_min_usd <= salary_max_usd", name="ck_jobs_salary_range"),
        UniqueConstraint("apply_url", name="uq_jobs_apply_url"),
        Index("ix_jobs_category_experience", "category", "experience_level"),
        Index("ix_jobs_location_country", "location", "country"),
        Index("ix_jobs_region", "region"),
        Index("ix_jobs_engineering_taxonomy", "engineering_branch", "domain"),
        Index("ix_jobs_is_live", "is_live"),
        Index("ix_jobs_posted_at", "posted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(160), nullable=False)
    country: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    region: Mapped[str | None] = mapped_column(String(40), nullable=True)
    engineering_branch: Mapped[str | None] = mapped_column(String(80), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_live: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    work_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    salary_min_usd: Mapped[float] = mapped_column(Float, nullable=False)
    salary_max_usd: Mapped[float] = mapped_column(Float, nullable=False)
    salary_display: Mapped[str | None] = mapped_column(String(160), nullable=True)
    salary_is_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    experience_level: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    apply_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
