"""Offline demo fixture helpers and a legacy synthetic-listing purge command.

Embeddings are deterministic, normalized feature-hash vectors. They are useful
for local similarity demos and preserve lexical similarity without an API key;
replace them with production model embeddings before using match scores for
real hiring decisions.

``build_rows`` is retained for deterministic unit fixtures only. Running this
script removes old demo rows and never inserts synthetic listings:
    python scripts/seed_dataset.py
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import random
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Keep the documented ``python scripts/seed_dataset.py`` invocation working
# without requiring an editable install of the backend package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SEED = 20261116
SOURCE = "hire-archy-seed"
COUNT = 150
CATEGORIES = ("Software Engineering", "Data Science", "AI/ML", "DevOps", "Product")
LEVELS = ("entry", "mid", "senior", "lead")
WORK_MODES = ("remote", "hybrid", "onsite")

ROLE_PROFILES = {
    "Software Engineering": {
        "titles": {
            "entry": ["Junior Backend Engineer", "Software Engineer I", "Frontend Engineer I", "Associate Full Stack Engineer"],
            "mid": ["Backend Engineer", "Full Stack Engineer", "Frontend Engineer", "Platform Software Engineer"],
            "senior": ["Senior Backend Engineer", "Senior Software Engineer", "Senior Frontend Engineer", "Staff Software Engineer"],
            "lead": ["Lead Software Engineer", "Principal Engineer", "Engineering Manager, Applications", "Staff Platform Engineer"],
        },
        "skill_groups": [
            ["Python", "FastAPI", "PostgreSQL", "REST APIs"],
            ["TypeScript", "React", "Next.js", "Node.js"],
            ["Java", "Spring Boot", "Kafka", "Microservices"],
            ["Go", "Kubernetes", "gRPC", "Distributed Systems"],
            ["C#", ".NET", "Azure", "SQL Server"],
            ["Ruby", "Rails", "Redis", "Sidekiq"],
        ],
        "focus": ["customer-facing applications", "reliable APIs", "developer platforms", "high-volume services"],
    },
    "Data Science": {
        "titles": {
            "entry": ["Junior Data Analyst", "Associate Data Scientist", "Product Data Analyst", "Analytics Associate"],
            "mid": ["Data Scientist", "Product Data Scientist", "Decision Scientist", "Analytics Engineer"],
            "senior": ["Senior Data Scientist", "Senior Product Data Scientist", "Senior Analytics Engineer", "Staff Data Scientist"],
            "lead": ["Lead Data Scientist", "Principal Data Scientist", "Analytics Lead", "Director, Data Science"],
        },
        "skill_groups": [
            ["Python", "SQL", "Pandas", "Scikit-Learn"],
            ["SQL", "dbt", "Snowflake", "Looker"],
            ["Python", "Causal Inference", "Experimentation", "Statistics"],
            ["Spark", "Databricks", "Airflow", "Delta Lake"],
            ["R", "Forecasting", "Time Series", "Tableau"],
            ["Python", "Feature Engineering", "XGBoost", "Model Monitoring"],
        ],
        "focus": ["product decisions", "customer behavior", "reliable metrics", "business forecasting"],
    },
    "AI/ML": {
        "titles": {
            "entry": ["Junior Machine Learning Engineer", "AI Research Associate", "Associate ML Scientist", "NLP Engineer I"],
            "mid": ["Machine Learning Engineer", "Applied Scientist", "NLP Engineer", "Computer Vision Engineer"],
            "senior": ["Senior ML Engineer", "Senior Applied Scientist", "Senior AI Engineer", "Staff Machine Learning Engineer"],
            "lead": ["Lead AI Engineer", "Principal Applied Scientist", "ML Research Lead", "Director, Applied AI"],
        },
        "skill_groups": [
            ["Python", "PyTorch", "Transformers", "NLP"],
            ["Python", "TensorFlow", "Computer Vision", "Model Serving"],
            ["LLMs", "RAG", "Vector Databases", "Evaluation"],
            ["PyTorch", "CUDA", "Distributed Training", "Deep Learning"],
            ["Python", "MLflow", "Feature Store", "MLOps"],
            ["JAX", "Research", "Generative AI", "Optimization"],
        ],
        "focus": ["production machine learning", "trustworthy AI systems", "language model applications", "model quality and evaluation"],
    },
    "DevOps": {
        "titles": {
            "entry": ["Junior DevOps Engineer", "Cloud Operations Engineer I", "Associate Site Reliability Engineer", "Platform Support Engineer"],
            "mid": ["DevOps Engineer", "Site Reliability Engineer", "Cloud Infrastructure Engineer", "Platform Engineer"],
            "senior": ["Senior Site Reliability Engineer", "Senior DevOps Engineer", "Senior Platform Engineer", "Cloud Architect"],
            "lead": ["Lead Platform Engineer", "Principal SRE", "Infrastructure Engineering Manager", "Director, Cloud Platform"],
        },
        "skill_groups": [
            ["AWS", "Terraform", "Kubernetes", "Docker"],
            ["GCP", "Pulumi", "GKE", "Prometheus"],
            ["Azure", "Bicep", "AKS", "Grafana"],
            ["Linux", "Ansible", "Jenkins", "CI/CD"],
            ["AWS", "Argo CD", "Helm", "GitOps"],
            ["Python", "OpenTelemetry", "Incident Response", "SLOs"],
        ],
        "focus": ["resilient cloud infrastructure", "developer productivity", "safe continuous delivery", "reliable production operations"],
    },
    "Product": {
        "titles": {
            "entry": ["Associate Product Manager", "Product Analyst", "Junior Technical Product Manager", "Product Operations Analyst"],
            "mid": ["Product Manager", "Technical Product Manager", "Growth Product Manager", "Product Operations Manager"],
            "senior": ["Senior Product Manager", "Senior Technical Product Manager", "Group Product Manager", "Principal Product Manager"],
            "lead": ["Lead Product Manager", "Director of Product", "Head of Product Analytics", "VP, Product Management"],
        },
        "skill_groups": [
            ["Product Strategy", "Roadmapping", "User Research", "SQL"],
            ["Experimentation", "A/B Testing", "Analytics", "Amplitude"],
            ["API Products", "Platform Strategy", "Technical Discovery", "Agile"],
            ["Go-to-Market", "Pricing", "Market Research", "Stakeholder Management"],
            ["Figma", "Prototyping", "Customer Interviews", "Product Discovery"],
            ["OKRs", "Product Analytics", "Looker", "Prioritization"],
        ],
        "focus": ["customer outcomes", "product discovery", "measurable growth", "clear product strategy"],
    },
}

COMPANIES = [
    ("Northstar Labs", "Series B"), ("Brightwell Health", "growth-stage"), ("Aster Cloud", "Series C"),
    ("Meridian Analytics", "profitable"), ("Juniper Commerce", "Series A"), ("LatticeWorks", "remote-first"),
    ("Atlas Robotics", "venture-backed"), ("Copperleaf Energy", "growth-stage"), ("Cinder Security", "Series B"),
    ("Harbor Financial", "established"), ("OpenField Systems", "remote-first"), ("Kiteframe", "Series A"),
    ("Mosaic Mobility", "growth-stage"), ("Redwood Bioinformatics", "venture-backed"), ("Bluepeak Networks", "established"),
    ("Evergreen Market", "Series C"), ("SignalForge", "Series B"), ("Orbit Learning", "profitable"),
    ("Pioneer Data Co.", "remote-first"), ("Cobalt Identity", "growth-stage"), ("Sundial Software", "Series A"),
    ("Cloudberry AI", "venture-backed"), ("Fieldnote", "Series B"), ("Keystone Logistics", "established"),
]

LOCATIONS = [
    ("San Francisco, CA", "United States"), ("New York, NY", "United States"),
    ("Austin, TX", "United States"), ("Seattle, WA", "United States"),
    ("Boston, MA", "United States"), ("Chicago, IL", "United States"),
    ("Toronto, ON", "Canada"), ("Vancouver, BC", "Canada"),
    ("London", "United Kingdom"), ("Berlin", "Germany"), ("Amsterdam", "Netherlands"),
    ("Dublin", "Ireland"), ("Bengaluru", "India"), ("Singapore", "Singapore"),
    ("Sydney, NSW", "Australia"), ("Remote - US", "United States"),
]

LEVEL_BANDS = {
    "entry": (65000, 105000),
    "mid": (95000, 155000),
    "senior": (135000, 215000),
    "lead": (170000, 270000),
}
CATEGORY_PREMIUM = {"Software Engineering": 1.00, "Data Science": 0.97, "AI/ML": 1.10, "DevOps": 1.04, "Product": 1.02}
EMBEDDING_DIMENSION = 1536


def build_embedding(text: str) -> list[float]:
    """Create an L2-normalized 1,536-d feature-hash vector from job text.

    Stable SHA-256 hashes map tokens and adjacent token pairs to signed buckets;
    L2 normalization scales the vector as x / sqrt(sum(x_i ** 2)). Shared role
    and skill language therefore gives related listings useful cosine similarity.
    """
    tokens = re.findall(r"[a-z0-9+#.-]+", text.lower())
    vector = [0.0] * EMBEDDING_DIMENSION
    features = tokens + [f"{left} {right}" for left, right in zip(tokens, tokens[1:])]
    for feature in features:
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSION
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[bucket] += sign
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude:
        vector = [value / magnitude for value in vector]
    return vector


def make_description(title: str, category: str, level: str, company_stage: str, focus: str, skills: list[str], rng: random.Random) -> str:
    """Compose varied but analytics-friendly job copy around the role profile."""
    level_copy = {
        "entry": "You will learn from experienced teammates while owning well-scoped projects.",
        "mid": "You will own features end to end and partner closely with engineering and business teams.",
        "senior": "You will set technical direction for complex projects and mentor other practitioners.",
        "lead": "You will shape the roadmap, establish team practices, and develop a high-performing group.",
    }[level]
    responsibilities = rng.choice([
        "Build and improve systems that support {focus}.",
        "Turn ambiguous problems in {focus} into reliable, measurable solutions.",
        "Partner with design, data, and engineering on {focus} initiatives.",
    ]).format(focus=focus)
    skills_text = ", ".join(skills)
    return (
        f"{title} at a {company_stage} company working in {category}. {responsibilities} "
        f"{level_copy} The team values thoughtful documentation, inclusive collaboration, and pragmatic delivery. "
        f"Useful experience includes {skills_text}. We welcome candidates with equivalent experience and a strong interest in {focus}."
    )


def build_rows() -> list[dict]:
    """Generate a stable, balanced set of 150 diverse job listing records."""
    rng = random.Random(SEED)
    now = datetime.now(timezone.utc)
    rows = []
    for index in range(COUNT):
        category = CATEGORIES[index % len(CATEGORIES)]
        # A shuffled level cycle gives each category a broad level mix.
        level = LEVELS[(index * 5) % len(LEVELS)]
        profile = ROLE_PROFILES[category]
        title = rng.choice(profile["titles"][level])
        company, stage = COMPANIES[(index * 7 + index // len(COMPANIES)) % len(COMPANIES)]
        city, country = LOCATIONS[(index * 5 + index // 9) % len(LOCATIONS)]
        work_mode = rng.choices(WORK_MODES, weights=(0.43, 0.35, 0.22), k=1)[0]
        skill_group = rng.choice(profile["skill_groups"])
        skills = list(skill_group)
        if rng.random() < 0.55:
            skills.append(rng.choice(profile["skill_groups"])[0])
        skills = list(dict.fromkeys(skills))
        focus = rng.choice(profile["focus"])

        low, high = LEVEL_BANDS[level]
        premium = CATEGORY_PREMIUM[category]
        regional_factor = 1.0 if country in ("United States", "Canada", "United Kingdom", "Australia", "Singapore") else 0.83
        center = rng.uniform(low, high) * premium * regional_factor
        spread = rng.uniform(0.12, 0.24)
        salary_min = round(center * (1 - spread) / 1000) * 1000
        salary_max = round(center * (1 + spread) / 1000) * 1000
        description = make_description(title, category, level, stage, focus, skills, rng)
        searchable_text = " ".join([title, category, level, focus, company, description, *skills])
        posted_at = now - timedelta(days=rng.randint(0, 89), hours=rng.randint(0, 23))
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        rows.append({
            "title": title,
            "company": company,
            "location": city,
            "country": country,
            "work_mode": work_mode,
            "salary_min_usd": float(salary_min),
            "salary_max_usd": float(max(salary_min, salary_max)),
            "experience_level": level,
            "description": description,
            "skills": skills,
            "category": category,
            "apply_url": f"https://careers.example.com/{index + 1:03d}/{slug}",
            "source": SOURCE,
            "posted_at": posted_at,
            "embedding": build_embedding(searchable_text),
        })
    return rows


async def seed() -> None:
    """Purge legacy demo/dummy rows without inserting non-genuine listings."""
    from sqlalchemy import delete, func, or_

    from app.db import AsyncSessionLocal
    from app.models import Job

    fake_sources = (SOURCE, "demo", "dummy", "synthetic", "test")
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(delete(Job).where(or_(
                Job.source.ilike("%hire-archy-seed%"),
                func.lower(Job.source).in_(fake_sources),
                Job.apply_url.ilike("%example.com%"),
            )))
            deleted = result.rowcount or 0
    print(f"Purged {deleted} synthetic/demo listings. No jobs were generated.")


if __name__ == "__main__":
    asyncio.run(seed())
