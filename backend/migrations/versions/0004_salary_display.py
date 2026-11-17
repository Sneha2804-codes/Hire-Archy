"""Store clean source-currency salary text alongside normalized USD values."""

from alembic import op
import sqlalchemy as sa

revision = "0004_salary_display"
down_revision = "0003_engineering_taxonomy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("jobs")}
    if "salary_display" not in columns:
        op.add_column("jobs", sa.Column("salary_display", sa.String(length=160), nullable=True))


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("jobs")}
    if "salary_display" in columns:
        op.drop_column("jobs", "salary_display")
