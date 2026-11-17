# Hire-Archy frontend

Next.js App Router UI for job discovery, candidate matching, and market analytics. It uses the local shadcn/ui component pattern with Radix primitives, Tailwind CSS, Lucide icons, and Recharts.

## Run locally

From the repository root, start PostgreSQL and Redis:

```powershell
docker compose up -d
```

In a backend terminal, prepare the database and start FastAPI:

```powershell
cd backend
uv sync --extra dev
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uv run alembic upgrade head
uv run python scripts/seed_dataset.py
uv run uvicorn app.main:app --reload --port 8000
```

In a second terminal, install dependencies and start Next.js:

```powershell
cd frontend
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
npm install
npm run dev
```

Open <http://localhost:3000>. The frontend reads `NEXT_PUBLIC_API_URL` from `.env.local`, defaulting to `http://localhost:8000/api`.

To verify the frontend:

```powershell
npm run build
npx tsc --noEmit
```
