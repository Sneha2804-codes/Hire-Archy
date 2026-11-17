# Hire-Archy backend

## Local setup

From `backend/`, install the backend and development dependencies, copy `.env.example` to `.env`, and apply the SQLite schema:

```powershell
uv sync --extra dev
Copy-Item .env.example .env
uv run alembic upgrade head
uv run python scripts/seed_dataset.py
```

The default database file is `hire_archy.db` in the backend directory. The API and seed script create missing SQLite tables automatically. The seed command replaces only rows whose source is `hire-archy-seed`; it inserts 150 listings across the five analytics categories. Its normalized feature-hash vectors are deterministic local demo embeddings and do not require an OpenAI API key.

## Live job ingestion

Set `OPENAI_API_KEY` in `backend/.env` to generate `text-embedding-3-small` vectors. Without a key or when the embedding service is unavailable, the ETL records a warning and uses local 1,536-dimensional feature-hash vectors so ingestion can still complete. Missing salary ranges are imputed from same-category/experience observations when available, otherwise from documented experience benchmarks; `salary_is_estimated` identifies those rows.

Install the Chromium binary once if you want the Playwright fallback to run when an HTTP feed request is rate-limited:

```powershell
uv run playwright install chromium
```

Run a one-off collection from `backend/`:

```powershell
uv run python -m app.etl.run --limit 25
```

The API exposes `POST /api/etl/run?limit=25` to schedule the same flow in a FastAPI background task and `GET /api/etl/logs` to read recent fetched, duplicate, and invalid counters.

## Matching and market analytics

- `POST /api/cv/upload` accepts a multipart `file` PDF, extracts profile fields, creates an embedding, and stores the candidate.
- `GET /api/jobs` filters by `q`, `category`, `work_mode`, `experience_level`, `min_salary`, repeated `skills`, `profile_id`, and `sort_by`; pagination uses `page` and `limit`.
- `GET /api/analytics/overview` returns skill demand, salary quartiles, and category/work-mode volume, with optional candidate skill-gap ROI via `profile_id`.

Candidate matching combines 50% semantic cosine similarity, 35% skill/keyword similarity (60% TF-IDF cosine and 40% canonical-skill Jaccard), and 15% experience-band alignment. Embeddings are stored as JSON arrays and semantic cosine similarity is calculated with NumPy in Python.

Run backend checks with:

```powershell
uv run pytest
```

The API can be started with `uv run uvicorn app.main:app --reload` from this directory.
