"""Batch embedding helpers with a deterministic no-key development fallback."""

from __future__ import annotations

import hashlib
import logging
import math
import re

logger = logging.getLogger(__name__)
EMBEDDING_DIMENSIONS = 1536


def local_embedding(text: str) -> list[float]:
    """Build a normalized signed feature-hash vector for offline/local runs."""
    tokens = re.findall(r"[a-z0-9+#.-]+", text.lower())
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for feature in tokens + [f"{a} {b}" for a, b in zip(tokens, tokens[1:])]:
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
        vector[index] += 1.0 if digest[4] & 1 else -1.0
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


async def embed_texts(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """Generate text-embedding-3-small vectors in batches, or local fallbacks.

    A missing key or failed OpenAI batch falls back locally so ETL can continue;
    fallback vectors are logged and remain 1,536-dimensional JSON lists.
    """
    if not texts:
        return []
    from app.config import settings

    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY is unset; using local feature-hash vectors for this ETL run")
        return [local_embedding(text) for text in texts]

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    output: list[list[float]] = []
    try:
        for start in range(0, len(texts), batch_size):
            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=texts[start : start + batch_size],
            )
            ordered = sorted(response.data, key=lambda item: item.index)
            output.extend(item.embedding for item in ordered)
        if len(output) != len(texts) or any(len(vector) != EMBEDDING_DIMENSIONS for vector in output):
            raise ValueError("Embedding API returned an unexpected count or vector dimension")
    except Exception:
        logger.exception("OpenAI embedding request failed; using local vectors for this batch")
        return [local_embedding(text) for text in texts]
    finally:
        await client.close()
    return output
