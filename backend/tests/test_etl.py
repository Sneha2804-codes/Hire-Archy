"""Unit tests for raw job normalization and deduplication."""

import pytest

from app.etl.cleaner import clean_jobs, normalize_company, normalize_title, parse_salary
from app.etl.scraper import parse_remoteok, parse_weworkremotely


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("$50-$75 / hour", (104000.0, 156000.0)),
        ("$8,000 - $10,000 monthly", (96000.0, 120000.0)),
        ("USD 100k–140k annually", (100000.0, 140000.0)),
        ("$100 k - $150 k annually", (100000.0, 150000.0)),
        ("$125,000 per year", (125000.0, 125000.0)),
        ("", (None, None)),
        ("€80k-€100k", (None, None)),
    ],
)
def test_parse_salary_annualizes_and_normalizes(raw, expected):
    assert parse_salary(raw) == expected


def test_normalize_title_and_company_remove_common_variants():
    assert normalize_title("Sr. Software Engineer") == normalize_title("Senior Software Engineer")
    assert normalize_company("Acme, Inc.") == normalize_company("ACME LLC")


def test_clean_jobs_normalizes_fields_extracts_skills_and_deduplicates():
    rows = [
        {
            "title": "Sr. Data Engineer",
            "company": "Acme, Inc.",
            "location": "  REMOTE   - USA ",
            "description": "Build analytics pipelines with React.js, ReactJS, Postgres, and Python.",
            "salary": "$80k-$120k",
            "apply_url": "https://example.com/job/1",
            "source": "Example",
        },
        {
            "title": "Senior Data Engineer",
            "company": "ACME LLC",
            "location": "Remote",
            "description": "Build data pipelines using Python and PostgreSQL.",
            "salary": "$90,000-$130,000",
            "apply_url": "https://example.com/job/2",
            "source": "Example Two",
        },
        {"title": "", "company": "Missing title", "apply_url": "https://example.com/invalid"},
    ]

    frame, stats = clean_jobs(rows)

    assert len(frame) == 1
    assert frame.iloc[0]["title"] == "Sr. Data Engineer"
    assert frame.iloc[0]["location"] == "Remote - United States"
    assert frame.iloc[0]["country"] == "United States"
    assert frame.iloc[0]["work_mode"] == "remote"
    assert "React" in frame.iloc[0]["skills"]
    assert "PostgreSQL" in frame.iloc[0]["skills"]
    assert "Python" in frame.iloc[0]["skills"]
    assert frame.iloc[0]["salary_min_usd"] == 80000
    assert stats == {"jobs_fetched": 3, "duplicates_skipped": 1, "invalid_dropped": 1}


def test_missing_salary_is_imputed_and_flagged():
    frame, _ = clean_jobs([{
        "title": "Junior Backend Engineer",
        "company": "Example Co",
        "location": "Austin, TX",
        "description": "Build Python and FastAPI services.",
        "apply_url": "https://example.com/jobs/backend",
    }])

    job = frame.iloc[0]
    assert job["salary_min_usd"] == 65000
    assert job["salary_max_usd"] == 95000
    assert bool(job["salary_is_estimated"])
    assert job["experience_level"] == "entry"
    assert job["work_mode"] == "onsite"


def test_parse_remoteok_public_json_shape():
    jobs = parse_remoteok([
        {"legal": "Remote OK feed terms"},
        {
            "position": "Data Engineer",
            "company": "Example Analytics",
            "location": "Remote",
            "description": "<p>Build data systems</p>",
            "tags": ["Python", "SQL"],
            "salary_min": 100000,
            "salary_max": 140000,
            "url": "/remote-jobs/123",
        },
    ], limit=1)

    assert len(jobs) == 1
    assert jobs[0]["company"] == "Example Analytics"
    assert jobs[0]["description"] == "Build data systems"
    assert jobs[0]["apply_url"] == "https://remoteok.com/remote-jobs/123"
    assert jobs[0]["salary_min_usd"] == 100000


def test_parse_weworkremotely_rss_shape():
    feed = """<?xml version="1.0"?><rss><channel><item>
      <title>Acme: Senior Python Engineer</title>
      <link>https://weworkremotely.com/remote-jobs/123</link>
      <description><![CDATA[<p>Build Python services.</p>]]></description>
      <category>Programming</category>
      <pubDate>Mon, 16 Nov 2026 10:00:00 GMT</pubDate>
    </item></channel></rss>"""

    jobs = parse_weworkremotely(feed, limit=1)

    assert len(jobs) == 1
    assert jobs[0]["title"] == "Senior Python Engineer"
    assert jobs[0]["company"] == "Acme"
    assert jobs[0]["work_mode"] == "remote"
    assert jobs[0]["source"] == "WeWorkRemotely"
