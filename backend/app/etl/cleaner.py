"""Normalize scraped job records into the database's analytics shape."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

import pandas as pd


# Approximate annual USD salary bands used only when a source supplies no pay.
# Each imputed record carries salary_is_estimated=True so it can be filtered out.
SALARY_BENCHMARKS: dict[str, tuple[int, int]] = {
    "entry": (65_000, 95_000),
    "mid": (95_000, 145_000),
    "senior": (140_000, 205_000),
    "lead": (175_000, 250_000),
}

CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("AI/ML", ("machine learning", "ml engineer", "artificial intelligence", " ai ", "llm", "deep learning", "nlp", "computer vision")),
    ("Data Science", ("data scientist", "data science", "data analyst", "analytics engineer", "statistician", "bi analyst")),
    ("DevOps", ("devops", "site reliability", " sre ", "platform engineer", "cloud infrastructure", "cloud engineer")),
    ("Product", ("product manager", "product owner", "product analyst", "product operations")),
)

SKILL_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("JavaScript", (r"javascript", r"\bjs\b")),
    ("TypeScript", (r"typescript", r"\bts\b")),
    ("React", (r"react(?:\.js|js)?",)),
    ("Next.js", (r"next(?:\.js|js)",)),
    ("Node.js", (r"node(?:\.js|js)",)),
    ("PostgreSQL", (r"postgres(?:ql)?",)),
    ("Scikit-learn", (r"scikit[ -]?learn", r"sklearn")),
    ("PyTorch", (r"pytorch",)),
    ("TensorFlow", (r"tensorflow",)),
    ("Python", (r"python",)),
    ("Java", (r"\bjava\b",)),
    ("C++", (r"c\+\+",)),
    ("C#", (r"c#", r"c sharp")),
    ("Go", (r"\bgo(lang)?\b",)),
    ("Ruby", (r"\bruby\b",)),
    ("PHP", (r"\bphp\b",)),
    ("Rust", (r"\brust\b",)),
    ("SQL", (r"\bsql\b",)),
    ("MySQL", (r"mysql",)),
    ("MongoDB", (r"mongo(?:db)?",)),
    ("Redis", (r"\bredis\b",)),
    ("Django", (r"django",)),
    ("FastAPI", (r"fastapi",)),
    ("Flask", (r"\bflask\b",)),
    ("GraphQL", (r"graphql",)),
    ("REST APIs", (r"rest(?:ful)? api", r"\brest\b")),
    ("AWS", (r"\baws\b", r"amazon web services")),
    ("Azure", (r"\bazure\b",)),
    ("Google Cloud", (r"google cloud", r"\bgcp\b")),
    ("Docker", (r"\bdocker\b",)),
    ("Kubernetes", (r"kubernetes", r"\bk8s\b")),
    ("Terraform", (r"terraform",)),
    ("CI/CD", (r"ci\s*/\s*cd", r"continuous integration", r"continuous delivery")),
    ("Pandas", (r"\bpandas\b",)),
    ("NumPy", (r"\bnumpy\b",)),
    ("Apache Spark", (r"apache spark", r"\bspark\b")),
    ("Airflow", (r"\bairflow\b",)),
    ("dbt", (r"\bdbt\b",)),
    ("Tableau", (r"\btableau\b",)),
    ("Power BI", (r"power\s*bi",)),
    ("Machine Learning", (r"machine learning", r"\bml\b")),
    ("LLMs", (r"\bllms?\b", r"large language models?")),
    ("LangChain", (r"langchain",)),
    ("Elasticsearch", (r"elasticsearch",)),
    ("Kafka", (r"\bkafka\b",)),
    ("Git", (r"\bgit\b",)),
)

COUNTRY_ALIASES = {
    "us": "United States", "usa": "United States", "united states": "United States",
    "uk": "United Kingdom", "united kingdom": "United Kingdom", "canada": "Canada",
    "india": "India", "germany": "Germany", "france": "France", "spain": "Spain",
    "netherlands": "Netherlands", "ireland": "Ireland", "australia": "Australia",
    "singapore": "Singapore", "brazil": "Brazil", "israel": "Israel",
}

COUNTRY_BY_CITY = {
    "san francisco": "United States", "new york": "United States", "austin": "United States",
    "seattle": "United States", "boston": "United States", "chicago": "United States",
    "los angeles": "United States", "toronto": "Canada", "vancouver": "Canada",
    "london": "United Kingdom", "berlin": "Germany", "amsterdam": "Netherlands",
    "dublin": "Ireland", "bengaluru": "India", "bangalore": "India", "singapore": "Singapore",
    "sydney": "Australia", "melbourne": "Australia", "paris": "France",
}


def _text(value: Any) -> str:
    """Convert common null-like values to safe normalized text."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value if item is not None)
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _number(token: str) -> float:
    """Parse a salary amount token, including comma grouping and k suffixes."""
    cleaned = token.strip().replace(",", "").replace(" ", "")
    suffix = cleaned[-1:].lower()
    multiplier = 1_000 if suffix == "k" else 1_000_000 if suffix == "m" else 1
    if suffix in {"k", "m"}:
        cleaned = cleaned[:-1]
    return float(cleaned) * multiplier


def parse_salary(value: Any, annual_hours: int = 2_080) -> tuple[float | None, float | None]:
    """Parse a pay string into an annual USD min/max pair.

    Hourly, daily, weekly, and monthly amounts are annualized using 2,080 work
    hours, 260 work days, 52 weeks, and 12 months. A bare amount/range is treated
    as annual. When text contains a non-USD currency symbol/code, it is left
    missing rather than silently mislabeled as USD.
    """
    salary = _text(value)
    if not salary:
        return None, None

    currency = re.search(r"\b(EUR|GBP|INR|CAD|AUD|SGD|JPY|EUR|GBP)\b|[€£₹¥]", salary, re.I)
    if currency:
        return None, None

    amounts = re.findall(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?:\s*[kKmM](?![a-zA-Z]))?", salary)
    parsed: list[float] = []
    for amount in amounts[:2]:
        try:
            parsed.append(_number(amount.replace(" ", "")))
        except ValueError:
            continue
    if not parsed:
        return None, None

    period_text = salary.lower()
    if re.search(r"/\s*(?:hr|hour)|\bper\s+hour|\bhourly\b", period_text):
        factor = annual_hours
    elif re.search(r"/\s*day|\bper\s+day|\bdaily\b", period_text):
        factor = 260
    elif re.search(r"/\s*week|\bper\s+week|\bweekly\b", period_text):
        factor = 52
    elif re.search(r"/\s*month|\bper\s+month|\bmonthly\b", period_text):
        factor = 12
    else:
        factor = 1

    low, high = min(parsed) * factor, max(parsed) * factor
    return round(low, 2), round(high, 2)


def normalize_title(value: Any) -> str:
    """Normalize title spelling and common seniority/abbreviation variants."""
    title = _text(value).lower().replace("&", " and ")
    title = re.sub(r"\b(sr|snr)\.?(?=\s|$)", "senior", title)
    title = re.sub(r"\bjr\.?(?=\s|$)", "junior", title)
    title = re.sub(r"\b(staff|principal)\b", "lead", title)
    title = re.sub(r"\b(engineer|engineering)\b", "engineer", title)
    title = re.sub(r"[^a-z0-9]+", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def normalize_company(value: Any) -> str:
    """Normalize company names and discard common legal suffixes."""
    company = re.sub(r"[^a-z0-9]+", " ", _text(value).lower())
    company = re.sub(r"\b(incorporated|inc|llc|ltd|limited|corp|corporation|gmbh|plc)\b", " ", company)
    return re.sub(r"\s+", " ", company).strip()


def _location(value: Any) -> str:
    """Standardize scraped location punctuation and whitespace."""
    location = re.sub(r"\s+", " ", _text(value))
    location = re.sub(r"\s*[,;|]\s*", ", ", location)
    location = re.sub(r"\s*[-–—]\s*", " - ", location)
    if re.search(r"\b(remote|anywhere|worldwide)\b", location, re.I):
        location = re.sub(r"\s+", " ", location.title()).strip()
    else:
        location = location.strip(" ,-") or "Unknown"
    location = re.sub(r"\bUsa\b", "United States", location)
    location = re.sub(r"\bUk\b", "United Kingdom", location)
    location = re.sub(r"\b(Ca|Tx|Wa|Ma|Il|Ny|Co|Fl|Or|Ga|Nc|Va)\b", lambda match: match.group(1).upper(), location)
    return location


def _country(record: dict[str, Any], location: str) -> str:
    """Infer country from supplied fields and common city names."""
    supplied = _text(record.get("country"))
    if supplied:
        return COUNTRY_ALIASES.get(supplied.lower(), supplied.title() if len(supplied) > 3 else supplied.upper())
    lower = location.lower()
    for alias, country in COUNTRY_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", lower):
            return country
    for city, country in COUNTRY_BY_CITY.items():
        if city in lower:
            return country
    if "remote" in lower and re.search(r"\b(us|usa|united states)\b", lower):
        return "United States"
    return "Unknown"


def _work_mode(record: dict[str, Any], location: str, description: str) -> str:
    """Infer remote, hybrid, or onsite from source fields and text hints."""
    value = _text(record.get("work_mode") or record.get("workplace_type") or record.get("remote"))
    if value.lower() in {"remote", "hybrid", "onsite", "on-site", "on site"}:
        return "onsite" if value.lower() in {"on-site", "on site"} else value.lower()
    combined = f"{value} {location} {description}".lower()
    if re.search(r"\bhybrid\b|flexible.{0,15}(?:office|remote)", combined):
        return "hybrid"
    if value.lower() in {"remote", "true", "yes"} or re.search(r"\bremote\b|work from anywhere|distributed team", combined):
        return "remote"
    return "onsite"


def _category(title: str, description: str, raw_category: str = "") -> str:
    """Map broad source taxonomies to the platform's five categories."""
    content = f" {raw_category.lower()} {title.lower()} {description.lower()} "
    if "software engineering" in content or "software developer" in content:
        return "Software Engineering"
    for category, keywords in CATEGORY_KEYWORDS:
        if any(keyword in content for keyword in keywords):
            return category
    return "Software Engineering"


def _experience(title: str, description: str, raw_level: str = "") -> str:
    """Infer the four supported experience levels from title/copy signals."""
    text = f"{raw_level} {title} {description}".lower()
    if re.search(r"\b(principal|staff|lead|director|head of|vp|vice president|10\+ years)\b", text):
        return "lead"
    if re.search(r"\b(senior|sr\.?|8\+ years|7\+ years)\b", text):
        return "senior"
    if re.search(r"\b(junior|jr\.?|entry.level|graduate|associate|intern)\b", text):
        return "entry"
    if raw_level.lower() in {"entry", "mid", "senior", "lead"}:
        return raw_level.lower()
    return "mid"


def extract_skills(record: dict[str, Any]) -> list[str]:
    """Extract canonical skills from provided tags, title, and description."""
    text = " ".join(
        _text(record.get(field))
        for field in ("title", "description", "skills", "tags", "technologies")
    ).lower()
    found = []
    for canonical, patterns in SKILL_PATTERNS:
        if any(re.search(pattern, text, re.I) for pattern in patterns):
            found.append(canonical)
    return found


def _salary_fields(record: dict[str, Any]) -> tuple[float | None, float | None, bool]:
    """Read explicit numeric salary fields first, then parse source text."""
    low, high = record.get("salary_min_usd"), record.get("salary_max_usd")
    try:
        low = float(low) if low not in (None, "") and not pd.isna(low) else None
    except (TypeError, ValueError):
        low = None
    try:
        high = float(high) if high not in (None, "") and not pd.isna(high) else None
    except (TypeError, ValueError):
        high = None
    if low is not None or high is not None:
        partial_range = low is None or high is None
        return (low if low is not None else high, high if high is not None else low, partial_range)
    parsed = parse_salary(record.get("salary") or record.get("salary_text") or record.get("compensation"))
    return parsed[0], parsed[1], parsed[0] is None or parsed[1] is None


def _is_duplicate(left: tuple[str, str], right: tuple[str, str], threshold: float) -> bool:
    """Require both title and company to match exactly or fuzzily."""
    if left == right:
        return True
    if not all(left) or not all(right):
        return False
    title_similarity = SequenceMatcher(None, left[0], right[0]).ratio()
    company_similarity = SequenceMatcher(None, left[1], right[1]).ratio()
    return title_similarity >= threshold and company_similarity >= threshold


def clean_jobs(records: list[dict[str, Any]], fuzzy_threshold: float = 0.90) -> tuple[pd.DataFrame, dict[str, int]]:
    """Clean and deduplicate raw source records.

    Returns a database-ready DataFrame and counters for fetched, duplicate, and
    invalid records. Missing salaries are benchmark-imputed by experience level;
    the salary_is_estimated column remains true for downstream filtering.
    """
    columns = [
        "title", "company", "location", "country", "work_mode", "salary_min_usd",
        "salary_max_usd", "salary_is_estimated", "experience_level", "description",
        "skills", "category", "apply_url", "source", "posted_at",
    ]
    jobs: list[dict[str, Any]] = []
    invalid_dropped = 0
    for record in records:
        title = re.sub(r"\s+", " ", _text(record.get("title") or record.get("position"))).strip()
        company = re.sub(r"\s+", " ", _text(record.get("company") or record.get("company_name"))).strip()
        apply_url = _text(record.get("apply_url") or record.get("url") or record.get("link"))
        description = _text(record.get("description") or record.get("details"))
        if not title or not company or not apply_url or not description:
            invalid_dropped += 1
            continue

        location = _location(record.get("location"))
        mode = _work_mode(record, location, description)
        category = _category(title, description, _text(record.get("category")))
        experience = _experience(title, description, _text(record.get("experience_level")))
        salary_min, salary_max, salary_is_estimated = _salary_fields(record)
        jobs.append({
            "title": title[:180],
            "company": company[:160],
            "location": location[:160],
            "country": _country(record, location)[:80],
            "work_mode": mode,
            "salary_min_usd": salary_min,
            "salary_max_usd": salary_max,
            "salary_is_estimated": salary_is_estimated,
            "experience_level": experience,
            "description": description,
            "skills": extract_skills(record),
            "category": category,
            "apply_url": apply_url[:500],
            "source": (_text(record.get("source")) or "unknown")[:100],
            "posted_at": record.get("posted_at") or record.get("date"),
            "_dedupe_key": (normalize_title(title), normalize_company(company)),
        })

    unique: list[dict[str, Any]] = []
    duplicate_count = 0
    for job in jobs:
        key = job["_dedupe_key"]
        duplicate = next((
            existing for existing in unique
            if job["apply_url"] == existing["apply_url"]
            or _is_duplicate(key, existing["_dedupe_key"], fuzzy_threshold)
        ), None)
        if duplicate is not None:
            duplicate_count += 1
            duplicate["skills"] = list(dict.fromkeys(duplicate["skills"] + job["skills"]))
            if duplicate["salary_is_estimated"] and not job["salary_is_estimated"]:
                for field in ("salary_min_usd", "salary_max_usd", "salary_is_estimated"):
                    duplicate[field] = job[field]
            if len(job["description"]) > len(duplicate["description"]):
                duplicate["description"] = job["description"]
            continue
        unique.append(job)

    # Infer missing ranges from observed comparable roles; use the category's
    # experience benchmark midpoint only when this batch has no comparable pay.
    frame = pd.DataFrame(unique)
    if frame.empty:
        return pd.DataFrame(columns=columns), {
            "jobs_fetched": len(records), "duplicates_skipped": duplicate_count,
            "invalid_dropped": invalid_dropped,
        }
    for index, job in frame[frame["salary_is_estimated"]].iterrows():
        comparable = frame.loc[
            (frame["category"] == job["category"])
            & (frame["experience_level"] == job["experience_level"])
            & (~frame["salary_is_estimated"])
        ]
        if not comparable.empty:
            midpoint = float(((comparable["salary_min_usd"] + comparable["salary_max_usd"]) / 2).median())
            low, high = round(midpoint * 0.9, 2), round(midpoint * 1.1, 2)
        else:
            benchmark_low, benchmark_high = SALARY_BENCHMARKS[job["experience_level"]]
            low, high = float(benchmark_low), float(benchmark_high)
        frame.at[index, "salary_min_usd"] = low
        frame.at[index, "salary_max_usd"] = high

    frame = frame.drop(columns=["_dedupe_key"])
    frame["posted_at"] = pd.to_datetime(frame["posted_at"], utc=True, errors="coerce")
    frame["posted_at"] = frame["posted_at"].fillna(pd.Timestamp.now(tz="UTC"))
    frame["skills"] = frame["skills"].apply(lambda skills: skills if isinstance(skills, list) else [])
    frame["salary_min_usd"] = frame["salary_min_usd"].astype(float)
    frame["salary_max_usd"] = frame["salary_max_usd"].astype(float)
    return frame[columns], {
        "jobs_fetched": len(records), "duplicates_skipped": duplicate_count,
        "invalid_dropped": invalid_dropped,
    }
