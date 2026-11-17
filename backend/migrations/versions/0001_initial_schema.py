"""Create the portable Hire-Archy schema with JSON vector storage."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("company", sa.String(length=160), nullable=False),
        sa.Column("location", sa.String(length=160), nullable=False),
        sa.Column("country", sa.String(length=80), nullable=False),
        sa.Column("work_mode", sa.String(length=20), nullable=False),
        sa.Column("salary_min_usd", sa.Float(), nullable=False),
        sa.Column("salary_max_usd", sa.Float(), nullable=False),
        sa.Column("experience_level", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("apply_url", sa.String(length=500), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.CheckConstraint("work_mode IN ('remote', 'hybrid', 'onsite')", name="ck_jobs_work_mode"),
        sa.CheckConstraint("experience_level IN ('entry', 'mid', 'senior', 'lead')", name="ck_jobs_experience_level"),
        sa.CheckConstraint(
            "category IN ('Software Engineering', 'Data Science', 'AI/ML', 'DevOps', 'Product')",
            name="ck_jobs_category",
        ),
        sa.CheckConstraint("salary_min_usd <= salary_max_usd", name="ck_jobs_salary_range"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("apply_url", name="uq_jobs_apply_url"),
    )
    op.create_index("ix_jobs_title", "jobs", ["title"])
    op.create_index("ix_jobs_company", "jobs", ["company"])
    op.create_index("ix_jobs_country", "jobs", ["country"])
    op.create_index("ix_jobs_category", "jobs", ["category"])
    op.create_index("ix_jobs_source", "jobs", ["source"])
    op.create_index("ix_jobs_category_experience", "jobs", ["category", "experience_level"])
    op.create_index("ix_jobs_location_country", "jobs", ["location", "country"])
    op.create_index("ix_jobs_posted_at", "jobs", ["posted_at"])

    op.create_table(
        "candidate_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("extracted_data", sa.JSON(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "scrape_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("jobs_fetched", sa.Integer(), nullable=False),
        sa.Column("duplicates_skipped", sa.Integer(), nullable=False),
        sa.Column("invalid_dropped", sa.Integer(), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scrape_runs_source", "scrape_runs", ["source"])


def downgrade() -> None:
    op.drop_index("ix_scrape_runs_source", table_name="scrape_runs")
    op.drop_table("scrape_runs")
    op.drop_table("candidate_profiles")
    for index_name in (
        "ix_jobs_posted_at",
        "ix_jobs_location_country",
        "ix_jobs_category_experience",
        "ix_jobs_source",
        "ix_jobs_category",
        "ix_jobs_country",
        "ix_jobs_company",
        "ix_jobs_title",
    ):
        op.drop_index(index_name, table_name="jobs")
    op.drop_table("jobs")
