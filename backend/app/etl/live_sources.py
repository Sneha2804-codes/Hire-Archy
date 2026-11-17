"""Quota-conscious collectors for authenticated and public live job sources.

Every returned record keeps the source's real apply URL. A record is discarded
when its URL is missing, non-HTTPS, or points at a reserved example domain.
"""

from __future__ import annotations

import asyncio
import html
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import settings

logger = logging.getLogger(__name__)
USER_AGENT = "Hire-Archy/1.0 (live job aggregation)"
ADZUNA_COUNTRIES = ("in", "sg", "au", "gb", "de", "us")
COUNTRY_INFO = {
    "in": ("India", "₹", "INR"), "sg": ("Singapore", "S$", "SGD"),
    "au": ("Australia", "A$", "AUD"), "gb": ("United Kingdom", "£", "GBP"),
    "de": ("Germany", "€", "EUR"), "us": ("United States", "$", "USD"),
}
REGION_COUNTRIES = {
    "India": ("in",),
    "APAC": ("sg", "au"),
    "Europe": ("gb", "de"),
    "North America": ("us",),
    "Middle East": (),
    "Global/Remote": ADZUNA_COUNTRIES,
}

# Eight calls exactly. The plan spans all requested Adzuna countries, all five
# core engineering query families, and both software/data query families.
ADZUNA_QUERY_PLAN = (
    ("in", "mechanical engineer"),
    ("in", "software engineer"),
    ("sg", "civil engineer"),
    ("au", "electrical engineer"),
    ("gb", "chemical engineer"),
    ("de", "manufacturing engineer"),
    ("us", "data analyst"),
    ("us", "mechanical engineer"),
)

GREENHOUSE_BOARDS = (
    "stripe", "cloudflare", "datadog", "nvidia", "anduril", "rippling", "atlassian", "retool",
)
LEVER_BOARDS = (
    "tesla", "jobyaviation", "anduril", "zoox", "aurora", "samsara", "waymo", "brex",
)
JOOBLE_LOCATIONS = (
    "India", "Bengaluru", "Hyderabad", "Pune", "Mumbai", "Chennai", "Singapore", "Sydney",
    "London", "Berlin", "New York", "San Francisco", "Dubai", "Abu Dhabi", "Riyadh", "Doha",
)


def _plain(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _is_real_https_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value.strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    return (
        parsed.scheme == "https"
        and bool(host)
        and host not in {"example.com", "example.org", "example.net", "example.invalid"}
        and not host.endswith(".example.com")
    )


def _posted_at(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _raw_job(
    *, title: Any, company: Any, location: Any, description: Any, apply_url: Any,
    source: str, posted_at: Any = None, salary: Any = None, salary_min: Any = None,
    salary_max: Any = None, salary_currency: str | None = None, skills: Any = None,
    work_mode: str | None = None,
) -> dict[str, Any] | None:
    url = str(apply_url or "").strip()
    if not _is_real_https_url(url) or not title or not company:
        return None
    return {
        "title": _plain(title),
        "company": _plain(company),
        "location": _plain(location) or "Remote",
        "description": _plain(description),
        "apply_url": url,
        "source": source,
        "posted_at": _posted_at(posted_at),
        "salary": str(salary or ""),
        "salary_min_native": salary_min,
        "salary_max_native": salary_max,
        "salary_currency": salary_currency,
        "skills": skills or [],
        "work_mode": work_mode,
    }


async def _get_json(client: httpx.AsyncClient, url: str, *, params: dict | None = None, source: str) -> Any:
    try:
        response = await client.get(url, params=params)
        if response.status_code == 429:
            logger.warning("%s rate limited this sync; skipping response", source)
            return None
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as error:
        status = getattr(getattr(error, "response", None), "status_code", None)
        logger.warning("%s request failed (%s)", source, status or type(error).__name__)
        return None


async def collect_adzuna_jobs(
    *, keywords: str | None = None, region: str | None = None, limit: int = 400,
) -> list[dict[str, Any]]:
    """Fetch at most eight Adzuna searches per call, handling HTTP 429 safely."""
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        logger.info("Adzuna credentials are unset; skipping Adzuna")
        return []
    selected_countries = set(REGION_COUNTRIES.get(region, ADZUNA_COUNTRIES)) if region else set(ADZUNA_COUNTRIES)
    plan = [(code, keywords or query) for code, query in ADZUNA_QUERY_PLAN if code in selected_countries]
    # Live-search remains bounded by the same eight-call cap.
    plan = plan[:8]
    if not plan:
        return []

    timeout = httpx.Timeout(18.0, connect=8.0)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        async def fetch(code: str, query: str) -> list[dict[str, Any]]:
            country, symbol, currency = COUNTRY_INFO[code]
            url = f"https://api.adzuna.com/v1/api/jobs/{code}/search/1"
            payload = await _get_json(client, url, source="Adzuna", params={
                "app_id": settings.adzuna_app_id,
                "app_key": settings.adzuna_app_key,
                "results_per_page": 50,
                "what": query,
                "where": country,
                "content-type": "application/json",
            })
            jobs = []
            for item in (payload or {}).get("results", []) if isinstance(payload, dict) else []:
                salary_min, salary_max = item.get("salary_min"), item.get("salary_max")
                salary_text = item.get("salary_is_predicted")
                display = f"{symbol}{salary_min:,.0f}–{symbol}{salary_max:,.0f} {currency}" if salary_min and salary_max else ""
                normalized = _raw_job(
                    title=item.get("title"), company=(item.get("company") or {}).get("display_name"),
                    location=(item.get("location") or {}).get("display_name") or country,
                    description=item.get("description"), apply_url=item.get("redirect_url"),
                    source="Adzuna", posted_at=item.get("created"), salary=display,
                    salary_min=salary_min, salary_max=salary_max, salary_currency=currency,
                    skills=item.get("category", {}).get("label", "").split(","),
                )
                if normalized:
                    normalized["country"] = country
                    normalized["salary_is_estimated"] = str(salary_text or "0") == "1"
                    jobs.append(normalized)
            return jobs

        # Calls run concurrently but the plan itself caps requests at eight.
        groups = await asyncio.gather(*(fetch(code, query) for code, query in plan), return_exceptions=True)
    valid_groups = [group for group in groups if isinstance(group, list)]
    return _round_robin(valid_groups, limit)


async def collect_jooble_jobs(
    *, keywords: str | None = None, region: str | None = None, limit: int = 80,
) -> list[dict[str, Any]]:
    """Query Jooble per supported regional hub, preserving returned apply links."""
    if not settings.jooble_api_key:
        logger.info("Jooble API key is unset; skipping Jooble")
        return []
    locations = list(JOOBLE_LOCATIONS)
    if region == "India":
        locations = ["India", "Bengaluru", "Hyderabad", "Pune", "Mumbai", "Chennai"]
    elif region == "APAC":
        locations = ["Singapore", "Sydney"]
    elif region == "Europe":
        locations = ["London", "Berlin"]
    elif region == "North America":
        locations = ["New York", "San Francisco"]
    elif region == "Middle East":
        locations = ["Dubai", "Abu Dhabi", "Riyadh", "Doha"]
    terms = keywords or "mechanical civil electrical chemical manufacturing software engineer data analyst"
    timeout = httpx.Timeout(18.0, connect=8.0)
    headers = {"User-Agent": USER_AGENT, "Content-Type": "application/json", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        async def fetch(location: str) -> list[dict[str, Any]]:
            try:
                response = await client.post(
                    f"https://jooble.org/api/{settings.jooble_api_key}",
                    json={"keywords": terms, "location": location, "page": 1},
                )
                if response.status_code == 429:
                    logger.warning("Jooble rate limited this sync; skipping %s", location)
                    return []
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError) as error:
                status = getattr(getattr(error, "response", None), "status_code", None)
                logger.warning("Jooble request failed for %s (%s)", location, status or type(error).__name__)
                return []
            output = []
            for item in payload.get("jobs", []) if isinstance(payload, dict) else []:
                job = _raw_job(
                    title=item.get("title"), company=item.get("company"), location=item.get("location") or location,
                    description=item.get("snippet") or item.get("description"), apply_url=item.get("link"),
                    source="Jooble", posted_at=item.get("updated"), salary=item.get("salary"),
                    work_mode="remote" if "remote" in f"{item.get('title', '')} {item.get('location', '')}".casefold() else None,
                )
                if job:
                    output.append(job)
            return output

        groups = await asyncio.gather(*(fetch(location) for location in locations), return_exceptions=True)
    return _round_robin([group for group in groups if isinstance(group, list)], limit)


async def collect_greenhouse_jobs(*, limit: int = 80) -> list[dict[str, Any]]:
    """Collect current postings from public Greenhouse job-board APIs."""
    timeout = httpx.Timeout(15.0, connect=7.0)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        async def fetch(board: str) -> list[dict[str, Any]]:
            payload = await _get_json(client, f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs", source="Greenhouse")
            out = []
            for item in (payload or {}).get("jobs", []) if isinstance(payload, dict) else []:
                location = (item.get("location") or {}).get("name")
                job = _raw_job(
                    title=item.get("title"), company=board.replace("-", " ").title(), location=location,
                    description=item.get("content"), apply_url=item.get("absolute_url"), source="Greenhouse",
                    posted_at=item.get("updated_at"),
                )
                if job:
                    out.append(job)
            return out
        groups = await asyncio.gather(*(fetch(board) for board in GREENHOUSE_BOARDS), return_exceptions=True)
    return _round_robin([group for group in groups if isinstance(group, list)], limit)


async def collect_lever_jobs(*, limit: int = 80) -> list[dict[str, Any]]:
    """Collect current postings from public Lever postings APIs."""
    timeout = httpx.Timeout(15.0, connect=7.0)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        async def fetch(board: str) -> list[dict[str, Any]]:
            payload = await _get_json(client, f"https://api.lever.co/v0/postings/{board}", source="Lever")
            out = []
            for item in payload if isinstance(payload, list) else []:
                categories = item.get("categories") or {}
                location = categories.get("location") or categories.get("allLocations") or ""
                job = _raw_job(
                    title=item.get("text"), company=board.replace("-", " ").title(), location=location,
                    description=item.get("descriptionPlain") or item.get("description"),
                    apply_url=item.get("hostedUrl") or item.get("applyUrl"), source="Lever",
                    posted_at=item.get("createdAt"),
                )
                if job:
                    out.append(job)
            return out
        groups = await asyncio.gather(*(fetch(board) for board in LEVER_BOARDS), return_exceptions=True)
    return _round_robin([group for group in groups if isinstance(group, list)], limit)


async def collect_arbeitnow_jobs(*, limit: int = 50) -> list[dict[str, Any]]:
    """Collect open listings from Arbeitnow's public job-board feed."""
    timeout = httpx.Timeout(15.0, connect=7.0)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        payload = await _get_json(client, "https://arbeitnow.com/api/job-board-api", source="Arbeitnow")
    jobs = []
    for item in (payload or {}).get("data", []) if isinstance(payload, dict) else []:
        job = _raw_job(
            title=item.get("title"), company=item.get("company_name"), location=item.get("location"),
            description=item.get("description"), apply_url=item.get("url"), source="Arbeitnow",
            posted_at=item.get("created_at"), skills=item.get("tags") or [],
            work_mode="remote" if item.get("remote") else None,
        )
        if job:
            jobs.append(job)
    return jobs[:limit]


async def collect_remotive_jobs(*, limit: int = 50, keywords: str | None = None) -> list[dict[str, Any]]:
    """Collect real remote listings from Remotive's public API."""
    timeout = httpx.Timeout(15.0, connect=7.0)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        payload = await _get_json(client, "https://remotive.com/api/remote-jobs", source="Remotive", params={"search": keywords} if keywords else None)
    jobs = []
    for item in (payload or {}).get("jobs", []) if isinstance(payload, dict) else []:
        job = _raw_job(
            title=item.get("title"), company=item.get("company_name"), location=item.get("candidate_required_location") or "Remote",
            description=item.get("description"), apply_url=item.get("url"), source="Remotive",
            posted_at=item.get("publication_date"), salary=item.get("salary"), skills=item.get("tags") or [], work_mode="remote",
        )
        if job:
            jobs.append(job)
    return jobs[:limit]


def _round_robin(groups: list[list[dict[str, Any]]], limit: int) -> list[dict[str, Any]]:
    """Interleave search results so one board/country cannot fill the batch."""
    output: list[dict[str, Any]] = []
    for index in range(max((len(group) for group in groups), default=0)):
        for group in groups:
            if index < len(group):
                output.append(group[index])
                if len(output) >= limit:
                    return output
    return output


async def collect_live_jobs(
    *, keywords: str | None = None, region: str | None = None, limit: int = 120,
) -> list[dict[str, Any]]:
    """Collect quota-bounded paid sources and always-active public feeds."""
    if limit < 1:
        return []
    terms = keywords or "engineering software data jobs"
    calls = await asyncio.gather(
        collect_adzuna_jobs(keywords=keywords, region=region, limit=limit),
        collect_jooble_jobs(keywords=keywords, region=region, limit=limit // 2 + 1),
        collect_greenhouse_jobs(limit=limit // 2 + 1),
        collect_lever_jobs(limit=limit // 2 + 1),
        collect_arbeitnow_jobs(limit=limit // 3 + 1),
        collect_remotive_jobs(limit=limit // 3 + 1, keywords=keywords),
        return_exceptions=True,
    )
    groups = [result for result in calls if isinstance(result, list)]
    return _round_robin(groups, limit)
