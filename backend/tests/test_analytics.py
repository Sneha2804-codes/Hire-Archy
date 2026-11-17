"""Tests for hybrid matching weights and market-level Pandas summaries."""

from app.analytics.matcher import composite_score, fallback_extract_profile, score_candidate_job
from app.analytics.market_stats import compute_market_stats


def test_composite_match_score_uses_documented_50_35_15_weights():
    result = composite_score(
        semantic_similarity=0.80,
        tfidf_similarity=0.50,
        skill_jaccard=0.25,
        experience_alignment=0.60,
    )

    # skill = .60*.50 + .40*.25 = .40
    # total = .50*.80 + .35*.40 + .15*.60 = .63
    assert result == {
        "total_score": 63.0,
        "semantic_score": 80.0,
        "skill_score": 40.0,
        "experience_score": 60.0,
        "tfidf_similarity": 50.0,
        "skill_jaccard": 25.0,
    }


def test_job_score_reports_semantic_and_explainable_skill_gaps():
    profile = {"skills": ["Python", "PostgreSQL"], "years_experience": 4}
    cv_text = "Python backend engineer with PostgreSQL experience"
    job = {
        "title": "Backend Engineer",
        "description": "Build APIs and data services with Python, PostgreSQL, and Docker.",
        "skills": ["Python", "PostgreSQL", "Docker"],
        "experience_level": "mid",
        "embedding": [1.0, 0.0],
    }

    result = score_candidate_job(profile, cv_text, [1.0, 0.0], job)

    assert result["semantic_score"] == 100.0
    assert result["matched_skills"] == ["Python", "PostgreSQL"]
    assert result["missing_skills"] == ["Docker"]
    assert 0 <= result["total_score"] <= 100


def test_offline_cv_parser_extracts_common_profile_fields():
    profile = fallback_extract_profile(
        """Avery Example
        Senior Software Engineer
        6 years of professional experience
        Skills: Python, ReactJS, PostgreSQL, AWS
        Education: Bachelor of Science in Computer Science
        Preferred roles: Backend Engineer, Platform Engineer
        """
    )

    assert profile["name"] == "Avery Example"
    assert profile["years_experience"] == 6
    assert {"Python", "React", "PostgreSQL", "AWS"}.issubset(set(profile["skills"]))
    assert any("Bachelor" in item for item in profile["education"])
    assert any("Backend Engineer" in item for item in profile["preferred_roles"])


def test_pandas_market_aggregations_cover_skills_salary_and_volume():
    jobs = [
        {
            "title": "Senior Data Engineer", "company": "Acme", "work_mode": "remote",
            "salary_min_usd": 100_000, "salary_max_usd": 120_000,
            "experience_level": "senior", "skills": ["Python", "SQL", "AWS"],
            "category": "Data Science", "embedding": [1.0, 0.0],
            "description": "Python SQL AWS data platform", "location": "Remote", "country": "US",
        },
        {
            "title": "Data Scientist", "company": "Beta", "work_mode": "remote",
            "salary_min_usd": 80_000, "salary_max_usd": 100_000,
            "experience_level": "mid", "skills": ["Python", "SQL", "Scikit-learn"],
            "category": "Data Science", "embedding": [1.0, 0.0],
            "description": "Python SQL machine learning", "location": "Remote", "country": "US",
        },
        {
            "title": "Product Manager", "company": "Gamma", "work_mode": "hybrid",
            "salary_min_usd": 120_000, "salary_max_usd": 160_000,
            "experience_level": "senior", "skills": ["Product Strategy", "SQL"],
            "category": "Product", "embedding": [1.0, 0.0],
            "description": "Product analytics strategy SQL", "location": "New York", "country": "US",
        },
    ]

    result = compute_market_stats(jobs)

    assert result["jobs_analyzed"] == 3
    assert result["median_salary_usd"] == 110_000
    assert result["remote_role_share"] == 0.6667
    top_skills = {row["skill"]: row for row in result["top_skills"]}
    assert top_skills["SQL"]["frequency"] == 3
    assert top_skills["SQL"]["mean_salary_usd"] == 113_333.33
    salary_groups = {
        (row["experience_level"], row["work_mode"]): row
        for row in result["salary_distribution"]
    }
    assert salary_groups[("senior", "remote")]["median"] == 110_000
    assert salary_groups[("senior", "remote")]["p25"] == 110_000
    volumes = {(row["category"], row["work_mode"]): row["job_count"] for row in result["job_volume"]}
    assert volumes[("Data Science", "remote")] == 2
    assert volumes[("Product", "hybrid")] == 1


def test_personal_skill_gap_roi_ranks_missing_skills_in_strong_matches():
    jobs = [
        {
            "title": "Python Engineer", "company": "Acme", "work_mode": "remote",
            "salary_min_usd": 100_000, "salary_max_usd": 130_000,
            "experience_level": "mid", "skills": ["Python", "SQL"],
            "category": "Software Engineering", "embedding": [1.0, 0.0],
            "description": "Python SQL backend services", "location": "Remote", "country": "US",
        },
        {
            "title": "Data Engineer", "company": "Beta", "work_mode": "remote",
            "salary_min_usd": 100_000, "salary_max_usd": 130_000,
            "experience_level": "mid", "skills": ["Python", "SQL", "AWS"],
            "category": "Data Science", "embedding": [1.0, 0.0],
            "description": "Python SQL AWS data pipelines", "location": "Remote", "country": "US",
        },
    ]

    result = compute_market_stats(
        jobs,
        profile={"skills": ["Python"], "years_experience": 4},
        cv_text="Python backend engineer",
        cv_embedding=[1.0, 0.0],
    )

    roi = {row["skill"]: row["high_scoring_jobs"] for row in result["personal_skill_gap_roi"]}
    assert roi["SQL"] == 2
    assert roi["AWS"] == 1
