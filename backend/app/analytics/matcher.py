"""CV extraction and transparent hybrid candidate-to-job scoring."""

from __future__ import annotations

import logging
import re
from typing import Any

import numpy as np

from app.etl.cleaner import extract_skills
from app.etl.embeddings import embed_texts

logger = logging.getLogger(__name__)

EXPERIENCE_BANDS: dict[str, tuple[float, float]] = {
    "entry": (0.0, 2.0),
    "mid": (2.0, 5.0),
    "senior": (5.0, 8.0),
    "lead": (8.0, 12.0),
}
EXPERIENCE_TOLERANCE_YEARS = 5.0


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from every page of an uploaded PDF using PyMuPDF."""
    import fitz

    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            pages = [page.get_text("text") for page in document]
    except Exception as error:
        raise ValueError("The uploaded file is not a readable PDF") from error
    text = "\n".join(page.strip() for page in pages if page.strip())
    if not text:
        raise ValueError("No selectable text was found in this PDF")
    return text


def fallback_extract_profile(raw_text: str) -> dict[str, Any]:
    """Extract useful profile fields with regex and the canonical skill list."""
    lines = [re.sub(r"\s+", " ", line).strip(" |\t") for line in raw_text.splitlines()]
    lines = [line for line in lines if line]
    name = ""
    for line in lines[:8]:
        if "@" in line or re.search(r"\d{3}[\s().-]*\d{3,}", line):
            continue
        if re.search(r"\b(resume|curriculum vitae|cv|engineer|developer|scientist|analyst|manager)\b", line, re.I):
            continue
        words = line.split()
        if 1 < len(words) <= 5 and all(re.search(r"[A-Za-z]", word) for word in words):
            name = line[:120]
            break

    year_matches = re.findall(
        r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:professional\s+)?(?:experience|exp\b)",
        raw_text,
        re.I,
    )
    years_experience = max((float(value) for value in year_matches), default=0.0)

    education_patterns = re.compile(
        r"\b(bachelor'?s?|master'?s?|ph\.?d\.?|doctorate|mba|b\.?s\.?|b\.?a\.?|m\.?s\.?|m\.?a\.?|b\.?tech|m\.?tech|associate degree)\b",
        re.I,
    )
    education = list(dict.fromkeys(line[:200] for line in lines if education_patterns.search(line)))[:10]
    role_lines = [
        line[:160]
        for line in lines
        if re.search(r"\b(engineer|developer|scientist|analyst|architect|product manager|designer|administrator)\b", line, re.I)
    ]
    preferred_match = re.search(
        r"(?:preferred|target|seeking|looking for)\s+(?:roles?|positions?|opportunities)?\s*[:\-]?\s*([^\n.;]{3,120})",
        raw_text,
        re.I,
    )
    preferred_roles = []
    if preferred_match:
        preferred_roles.extend(re.split(r",|\bor\b|\band\b|/", preferred_match.group(1)))
    preferred_roles.extend(role_lines[:4])
    preferred_roles = list(dict.fromkeys(item.strip(" :,-") for item in preferred_roles if item.strip(" :,-")))[:8]

    return {
        "name": name or "Unknown Candidate",
        "years_experience": years_experience,
        "skills": extract_skills({"description": raw_text}),
        "education": education,
        "preferred_roles": preferred_roles,
    }


async def extract_candidate_profile(raw_text: str) -> dict[str, Any]:
    """Use GPT-4o-mini Structured Outputs when configured; fall back offline."""
    from app.config import settings

    if not settings.openai_api_key:
        logger.info("OPENAI_API_KEY is unset; using regex/keyword CV extraction")
        return fallback_extract_profile(raw_text)

    try:
        from openai import AsyncOpenAI
        from pydantic import BaseModel, Field

        class CandidateExtraction(BaseModel):
            name: str = Field(description="Candidate's full name, or Unknown Candidate")
            years_experience: float = Field(ge=0, description="Total professional experience in years")
            skills: list[str]
            education: list[str]
            preferred_roles: list[str]

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        try:
            response = await client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Extract candidate facts from the CV. Do not infer personal data that is not present. "
                            "Use canonical technical skill names (React, PostgreSQL, Python, etc.). "
                            "If years of experience is unclear, return 0."
                        ),
                    },
                    {"role": "user", "content": raw_text[:40_000]},
                ],
                response_format=CandidateExtraction,
            )
            parsed = response.choices[0].message.parsed
            if parsed is None:
                raise ValueError("Structured extraction returned no parsed profile")
            result = parsed.model_dump()
            result["skills"] = list(dict.fromkeys(
                extract_skills({"skills": result.get("skills", []), "description": " ".join(result.get("skills", []))})
            ))
            return result
        finally:
            await client.close()
    except Exception:
        logger.exception("Structured CV extraction failed; using local parser")
        return fallback_extract_profile(raw_text)


def _cosine(left: list[float] | None, right: list[float] | None) -> float:
    """Return NumPy cosine similarity; absent or incompatible vectors score 0."""
    if left is None or right is None:
        return 0.0
    left_array = np.asarray(left, dtype=np.float64)
    right_array = np.asarray(right, dtype=np.float64)
    if left_array.ndim != 1 or right_array.ndim != 1 or left_array.shape != right_array.shape:
        return 0.0
    denominator = float(np.linalg.norm(left_array) * np.linalg.norm(right_array))
    if not denominator:
        return 0.0
    similarity = float(np.dot(left_array, right_array) / denominator)
    return max(0.0, min(1.0, similarity))


def _tfidf_cosine(cv_text: str, job_text: str) -> float:
    """Compute TF-IDF cosine, using a simple overlap fallback if sklearn is absent."""
    if not cv_text.strip() or not job_text.strip():
        return 0.0
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform([cv_text, job_text])
        return float(cosine_similarity(matrix[0:1], matrix[1:2])[0, 0])
    except ImportError:
        cv_terms = set(re.findall(r"[a-z0-9+#.]+", cv_text.lower()))
        job_terms = set(re.findall(r"[a-z0-9+#.]+", job_text.lower()))
        return len(cv_terms & job_terms) / max(1, len(cv_terms | job_terms))
    except ValueError:  # e.g. both documents contain only English stop words
        return 0.0


def _experience_alignment(years_experience: float | int | None, experience_level: str) -> float:
    """Score numeric years against level bands, with 5-year linear falloff.

    A candidate within the level's expected years band receives 1.0. Outside
    the band, the score is 1 - distance / 5, clamped to [0, 1]. Missing years
    receive a neutral 0.5 because the evidence is unknown rather than negative.
    """
    if years_experience is None:
        return 0.5
    try:
        years = max(0.0, float(years_experience))
    except (TypeError, ValueError):
        return 0.5
    low, high = EXPERIENCE_BANDS.get(str(experience_level).lower(), EXPERIENCE_BANDS["mid"])
    distance = low - years if years < low else years - high if years > high else 0.0
    return max(0.0, 1.0 - distance / EXPERIENCE_TOLERANCE_YEARS)


def composite_score(
    semantic_similarity: float,
    tfidf_similarity: float,
    skill_jaccard: float,
    experience_alignment: float,
) -> dict[str, float]:
    """Apply the documented 50/35/15 formula and 60/40 text-skill sub-blend.

    Skill score = 0.60 * TF-IDF cosine + 0.40 * skill Jaccard.
    Total score = 0.50 * semantic + 0.35 * skill score + 0.15 * experience.
    Inputs and component outputs are proportions in [0, 1]; returned values
    are percentages in [0, 100].
    """
    semantic = max(0.0, min(1.0, semantic_similarity))
    tfidf = max(0.0, min(1.0, tfidf_similarity))
    jaccard = max(0.0, min(1.0, skill_jaccard))
    experience = max(0.0, min(1.0, experience_alignment))
    skill = 0.60 * tfidf + 0.40 * jaccard
    return {
        "total_score": round(100 * (0.50 * semantic + 0.35 * skill + 0.15 * experience), 2),
        "semantic_score": round(100 * semantic, 2),
        "skill_score": round(100 * skill, 2),
        "experience_score": round(100 * experience, 2),
        "tfidf_similarity": round(100 * tfidf, 2),
        "skill_jaccard": round(100 * jaccard, 2),
    }


def _value(item: Any, key: str, default: Any = None) -> Any:
    """Read a field from a SQLAlchemy model or an ordinary mapping."""
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def score_candidate_job(
    profile: dict[str, Any],
    cv_text: str,
    cv_embedding: list[float] | None,
    job: Any,
    semantic_similarity: float | None = None,
) -> dict[str, Any]:
    """Return the composite match and explainable matched/missing skills."""
    job_skills = list(dict.fromkeys(_value(job, "skills", []) or []))
    candidate_skills = list(dict.fromkeys(profile.get("skills", []) or []))
    if not candidate_skills and cv_text:
        candidate_skills = extract_skills({"description": cv_text})
    candidate_set = {str(skill).casefold() for skill in candidate_skills}
    job_set = {str(skill).casefold() for skill in job_skills}
    matched = [skill for skill in job_skills if str(skill).casefold() in candidate_set]
    missing = [skill for skill in job_skills if str(skill).casefold() not in candidate_set]
    union = candidate_set | job_set
    jaccard = len(candidate_set & job_set) / len(union) if union else 0.0

    job_text = " ".join((
        str(_value(job, "title", "")),
        str(_value(job, "description", "")),
        " ".join(str(skill) for skill in job_skills),
    ))
    signals = composite_score(
        _cosine(cv_embedding, _value(job, "embedding")) if semantic_similarity is None else semantic_similarity,
        _tfidf_cosine(cv_text, job_text),
        jaccard,
        _experience_alignment(profile.get("years_experience"), _value(job, "experience_level", "mid")),
    )
    return {**signals, "matched_skills": matched, "missing_skills": missing}


async def embed_cv(raw_text: str) -> list[float]:
    """Generate the same 1,536-dimensional embedding family used by job ETL."""
    return (await embed_texts([raw_text]))[0]
