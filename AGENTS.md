# AGENTS.md

## Project

Hire-Archy — An Intelligent Job Aggregation, CV Matching, and Labor Market Data Analysis Web Platform.

## Architecture

- `/backend`: Python 3.11+, FastAPI, SQLAlchemy (async), PostgreSQL + pgvector, Pandas, Scikit-Learn, PyMuPDF, OpenAI SDK, and Playwright.
- `/frontend`: Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui, and Recharts.

## UI & Aesthetic Standards

- Use a dark-mode-first editorial SaaS aesthetic: zinc-950 background, zinc-900/70 cards, crisp 1px borders, and emerald/indigo data accents.
- Maintain high visual polish. Never use Streamlit or unstyled HTML.

## Data Science Rigor

All data cleaning, normalization, TF-IDF vectorization, cosine similarity scoring, and market aggregations must be cleanly modularized in `/backend/app/analytics/`, with docstrings explaining the formulas used.

## Verification

- Run `pytest` after every backend change.
- Run `npm run build` after every frontend change.
