"""Track whether missing job salaries were imputed by the ETL pipeline."""

from alembic import op
import sqlalchemy as sa

revision = "0002_salary_estimate_flag"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("salary_is_estimated", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("jobs", "salary_is_estimated")
