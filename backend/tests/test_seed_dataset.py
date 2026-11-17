"""Checks for the deterministic analytics seed dataset."""

from collections import Counter

from scripts.seed_dataset import CATEGORIES, COUNT, LEVELS, WORK_MODES, build_embedding, build_rows


def test_seed_rows_cover_analytics_dimensions():
    rows = build_rows()

    assert len(rows) == COUNT == 150
    assert set(row["category"] for row in rows) == set(CATEGORIES)
    assert set(row["experience_level"] for row in rows) == set(LEVELS)
    assert set(row["work_mode"] for row in rows) == set(WORK_MODES)
    assert len({row["country"] for row in rows}) >= 8
    assert all(row["salary_min_usd"] <= row["salary_max_usd"] for row in rows)
    assert all(3 <= len(row["skills"]) <= 5 for row in rows)
    assert all(len(row["embedding"]) == 1536 for row in rows)
    assert all(row["source"] == "hire-archy-seed" for row in rows)
    assert all(row["apply_url"] for row in rows)


def test_seed_distribution_is_varied_and_deterministic():
    first = build_rows()
    second = build_rows()

    category_counts = Counter(row["category"] for row in first)
    level_counts = Counter(row["experience_level"] for row in first)
    assert set(category_counts.values()) == {30}
    assert max(level_counts.values()) - min(level_counts.values()) <= 3
    assert [(row["title"], row["skills"]) for row in first] == [
        (row["title"], row["skills"]) for row in second
    ]


def test_local_embedding_is_normalized_and_text_sensitive():
    python_vector = build_embedding("Python FastAPI PostgreSQL backend engineering")
    ml_vector = build_embedding("PyTorch machine learning neural network model")

    assert len(python_vector) == 1536
    assert abs(sum(value * value for value in python_vector) - 1) < 1e-6
    assert python_vector != ml_vector
