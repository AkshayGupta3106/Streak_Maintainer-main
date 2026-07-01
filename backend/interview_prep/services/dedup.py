"""
Embedding-based dedup so you don't repeat questions from the last 30 days.
Uses Gemini's embedding model (free) — no separate service needed.
"""
import math
import google.generativeai as genai
from django.utils import timezone
from datetime import timedelta

from ..models import DailyInterviewQuestion

SIMILARITY_THRESHOLD = 0.85


def embed_text(text: str) -> list[float]:
    result = genai.embed_content(model="models/embedding-001", content=text)
    return result["embedding"]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def is_duplicate(new_embedding: list[float], lookback_days: int = 30) -> bool:
    cutoff = timezone.now().date() - timedelta(days=lookback_days)
    recent = DailyInterviewQuestion.objects.filter(
        date_generated__gte=cutoff, embedding__isnull=False
    ).values_list("embedding", flat=True)

    for existing_embedding in recent:
        if cosine_similarity(new_embedding, existing_embedding) >= SIMILARITY_THRESHOLD:
            return True
    return False
