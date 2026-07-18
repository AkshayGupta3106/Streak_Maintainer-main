"""
Embedding-based dedup so you don't repeat questions from the last 30 days.
Uses Gemini's embedding model (free) — no separate service needed.
"""
import logging
import math
import os
from datetime import timedelta

from django.utils import timezone
from google import genai

from ..models import DailyInterviewQuestion

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.85
EMBEDDING_MODEL = "gemini-embedding-2"

_client = None


def _get_client():
    """Lazily create the client so a missing key doesn't blow up at import time."""
    global _client
    if _client is None and os.environ.get("GEMINI_API_KEY"):
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def embed_text(text: str) -> list[float] | None:
    client = _get_client()
    if client is None:
        return None
    try:
        result = client.models.embed_content(model=EMBEDDING_MODEL, contents=text)
        return list(result.embeddings[0].values)
    except Exception as e:
        logger.warning(f"Failed to embed text: {e}")
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def is_duplicate(new_embedding: list[float], lookback_days: int = 30) -> bool:
    if not new_embedding:
        return False
    cutoff = timezone.now().date() - timedelta(days=lookback_days)
    recent = DailyInterviewQuestion.objects.filter(
        date_generated__gte=cutoff, embedding__isnull=False
    ).values_list("embedding", flat=True)

    for existing_embedding in recent:
        if cosine_similarity(new_embedding, existing_embedding) >= SIMILARITY_THRESHOLD:
            return True
    return False