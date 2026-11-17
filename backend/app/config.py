"""Application configuration loaded from environment variables."""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_PATH = (BACKEND_DIR / "hire_archy.db").resolve()
DEFAULT_DATABASE_URL = URL.create(
    drivername="sqlite+aiosqlite",
    database=str(DEFAULT_DATABASE_PATH),
).render_as_string(hide_password=False)


class Settings(BaseSettings):
    """Runtime settings with local SQLite as the zero-configuration default."""

    database_url: str = DEFAULT_DATABASE_URL
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str | None = None
    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None
    jooble_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def anchor_sqlite_database_to_backend(cls, value: str) -> str:
        """Resolve relative SQLite paths against this backend, not the shell cwd."""
        if not isinstance(value, str):
            return value
        try:
            url = make_url(value)
        except Exception:
            return value
        if not url.drivername.startswith("sqlite") or not url.database or url.database == ":memory:":
            return value

        database_path = Path(url.database)
        if not database_path.is_absolute():
            database_path = BACKEND_DIR / database_path
        return URL.create(
            drivername=url.drivername,
            database=str(database_path.resolve()),
        ).render_as_string(hide_password=False)


settings = Settings()
