"""Add live-listing, region, and engineering taxonomy fields to jobs."""

from alembic import op
import sqlalchemy as sa

revision = "0003_engineering_taxonomy"
down_revision = "0002_salary_estimate_flag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("jobs")}
    if "region" not in columns:
        op.add_column("jobs", sa.Column("region", sa.String(length=40), nullable=True))
    if "engineering_branch" not in columns:
        op.add_column("jobs", sa.Column("engineering_branch", sa.String(length=80), nullable=True))
    if "domain" not in columns:
        op.add_column("jobs", sa.Column("domain", sa.String(length=100), nullable=True))
    if "is_live" not in columns:
        op.add_column("jobs", sa.Column("is_live", sa.Boolean(), server_default=sa.true(), nullable=False))

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("jobs")}
    for name, fields in (
        ("ix_jobs_region", ["region"]),
        ("ix_jobs_engineering_taxonomy", ["engineering_branch", "domain"]),
        ("ix_jobs_is_live", ["is_live"]),
    ):
        if name not in indexes:
            op.create_index(name, "jobs", fields, unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("jobs")}
    for name in ("ix_jobs_is_live", "ix_jobs_engineering_taxonomy", "ix_jobs_region"):
        if name in indexes:
            op.drop_index(name, table_name="jobs")
    columns = {column["name"] for column in sa.inspect(bind).get_columns("jobs")}
    for name in ("is_live", "domain", "engineering_branch", "region"):
        if name in columns:
            op.drop_column("jobs", name)
