"""Collectors for public Remote OK JSON and We Work Remotely RSS feeds."""

from __future__ import annotations

import asyncio
import html
import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any


logger = logging.getLogger(__name__)

REMOTEOK_URL = "https://remoteok.com/api"
WWR_URL = "https://weworkremotely.com/remote-jobs.rss"
USER_AGENT = "Hire-Archy/0.1 (public job feed collection)"


def _plain_text(value: Any) -> str:
    """Remove markup from descriptions while retaining readable spacing."""
    text = html.unescape(str(value or ""))
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _date(value: Any) -> datetime | None:
    """Parse common ISO/RSS timestamps into timezone-aware UTC values."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(str(value))
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_remoteok(payload: Any, limit: int | None = None) -> list[dict[str, Any]]:
    """Normalize Remote OK public JSON items to raw ETL records."""
    jobs = []
    if not isinstance(payload, list):
        return jobs
    for item in payload:
        if not isinstance(item, dict) or not (item.get("position") or item.get("title")):
            continue
        url = item.get("apply_url") or item.get("url") or ""
        if url.startswith("/"):
            url = f"https://remoteok.com{url}"
        tags = item.get("tags") or []
        jobs.append({
            "title": item.get("position") or item.get("title"),
            "company": item.get("company") or item.get("company_name"),
            "location": item.get("location") or ("Remote" if item.get("remote") else "Unknown"),
            "work_mode": "remote" if item.get("remote", True) else item.get("work_mode"),
            "description": _plain_text(item.get("description") or item.get("body")),
            "skills": tags,
            "category": item.get("category") or "",
            "salary_min_usd": item.get("salary_min") or None,
            "salary_max_usd": item.get("salary_max") or None,
            "salary": item.get("salary") or item.get("salary_string"),
            "apply_url": url,
            "posted_at": _date(item.get("date") or item.get("publication_date")),
            "source": "RemoteOK",
        })
        if limit is not None and len(jobs) >= limit:
            break
    return jobs


def parse_weworkremotely(xml_body: str, limit: int | None = None) -> list[dict[str, Any]]:
    """Normalize the public We Work Remotely RSS feed into raw ETL records."""
    jobs = []
    try:
        root = ET.fromstring(xml_body)
    except ET.ParseError:
        logger.warning("Could not parse We Work Remotely RSS payload")
        return jobs
    for item in root.findall(".//item"):
        full_title = _plain_text(item.findtext("title"))
        link = _plain_text(item.findtext("link"))
        description = _plain_text(item.findtext("description"))
        category = _plain_text(item.findtext("category"))
        # WWR commonly formats feed titles as "Company: Job title".
        if ": " in full_title:
            company, title = full_title.split(": ", 1)
        elif " at " in full_title:
            title, company = full_title.rsplit(" at ", 1)
        else:
            company, title = "Unknown Company", full_title
        if not title or not link:
            continue
        jobs.append({
            "title": title,
            "company": company,
            "location": "Remote",
            "work_mode": "remote",
            "description": description,
            "category": category,
            "salary": "",
            "apply_url": link,
            "posted_at": _date(item.findtext("pubDate")),
            "source": "WeWorkRemotely",
        })
        if limit is not None and len(jobs) >= limit:
            break
    return jobs


async def _playwright_payload(url: str) -> str:
    """Fetch feed content in Chromium when the direct HTTP request is blocked."""
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            page = await browser.new_page(user_agent=USER_AGENT)
            response = await page.goto(url, wait_until="domcontentloaded", timeout=25_000)
            if response is not None and response.status >= 400:
                raise RuntimeError(f"Browser fallback returned HTTP {response.status}")
            if response is not None:
                return await response.text()
            return await page.locator("body").inner_text()
        finally:
            await browser.close()


async def _fetch_source(url: str, source: str, limit: int) -> list[dict[str, Any]]:
    """Try httpx first and use Playwright for rate limits or transport errors."""
    import httpx

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json, application/rss+xml, application/xml, text/xml, */*"}
    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0), follow_redirects=True, headers=headers) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            body = response.text
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError) as error:
            status = getattr(getattr(error, "response", None), "status_code", None)
            logger.warning("%s HTTP fetch failed (%s); trying Playwright fallback", source, status or type(error).__name__)
            try:
                body = await _playwright_payload(url)
            except Exception:
                logger.exception("%s Playwright fallback failed", source)
                return []
    try:
        if source == "RemoteOK":
            return parse_remoteok(json.loads(body), limit)
        return parse_weworkremotely(body, limit)
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.exception("Could not decode %s feed", source)
        return []


async def collect_remoteok(limit: int = 25) -> list[dict[str, Any]]:
    """Collect recent Remote OK listings through JSON with browser fallback."""
    return await _fetch_source(REMOTEOK_URL, "RemoteOK", limit)


async def collect_weworkremotely(limit: int = 25) -> list[dict[str, Any]]:
    """Collect recent We Work Remotely listings through RSS with browser fallback."""
    return await _fetch_source(WWR_URL, "WeWorkRemotely", limit)


async def collect_jobs(limit: int = 25) -> list[dict[str, Any]]:
    """Collect up to ``limit`` records, splitting the budget across sources."""
    if limit < 1:
        return []
    first_limit = (limit + 1) // 2
    second_limit = limit // 2
    collectors = [collect_remoteok(first_limit)]
    if second_limit:
        collectors.append(collect_weworkremotely(second_limit))
    results = await asyncio.gather(*collectors, return_exceptions=True)
    combined: list[dict[str, Any]] = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(
                "A job source collector failed: %s",
                result,
                exc_info=(type(result), result, result.__traceback__),
            )
            continue
        combined.extend(result)
    return combined[:limit]
