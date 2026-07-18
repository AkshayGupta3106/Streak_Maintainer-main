"""
Pulls recent signal on what's actually being asked in AI/DS interviews.
Uses ddgs (DuckDuckGo search wrapper) — no API key required.
"""
import logging
import random
import re
import time
from ddgs import DDGS

logger = logging.getLogger(__name__)

TOPIC_TEMPLATES = [
    # Glassdoor-style interview reports
    'site:glassdoor.com ("machine learning engineer" OR "data scientist" OR "ai engineer") interview questions',
    # Reddit (requested source) with ML-specific communities
    'site:reddit.com ("r/MachineLearning" OR "r/datascience") interview questions',
    # LeetCode discussion threads for company interview patterns
    'site:leetcode.com/discuss ("machine learning" OR "data scientist" OR "interview")',
    # General interview posts and blogs
    '("ai engineer interview" OR "ml engineer interview" OR "data scientist interview") (questions OR experience OR process)',
    # Fresh GenAI/system-design emphasis
    '("LLM" OR "GenAI" OR "RAG") interview (questions OR system design) 2026',
]

FRESHNESS_HINTS = [
    "2026",
    "2025",
    "recent",
    "last month",
    "this year",
    "new",
]

SOURCE_BOOSTS = {
    "reddit.com": 3,
    "glassdoor.com": 3,
    "leetcode.com/discuss": 3,
}


def build_daily_queries(n_queries: int = 4) -> list[str]:
    """Pick a rotating subset of source-targeted queries for today's run."""
    query_count = min(n_queries, len(TOPIC_TEMPLATES))
    templates = random.sample(TOPIC_TEMPLATES, k=query_count)
    freshness = random.choice(FRESHNESS_HINTS)
    queries = [f"{t} {freshness}" for t in templates]
    return queries


def _detect_source(url: str) -> str:
    url_lower = (url or "").lower()
    if "reddit.com" in url_lower:
        return "reddit"
    if "glassdoor.com" in url_lower:
        return "glassdoor"
    if "leetcode.com/discuss" in url_lower:
        return "leetcode_discuss"
    return "web"


def _score_result(query: str, result: dict) -> int:
    text = " ".join([
        query or "",
        result.get("title", ""),
        result.get("body", ""),
    ]).lower()
    href = (result.get("href") or "").lower()

    score = 0

    for domain, boost in SOURCE_BOOSTS.items():
        if domain in href:
            score += boost

    # Prefer interview-experience style threads over generic listicles.
    for token in ["interview", "asked", "experience", "process", "questions"]:
        if token in text:
            score += 1

    if re.search(r"\b(2026|2025)\b", text):
        score += 2
    elif "recent" in text:
        score += 1

    return score


def search_ddg(query: str, max_results: int = 5) -> list[dict]:
    """
    Returns list of {title, href, body} dicts.
    Rate-limit yourself — DDG will block aggressive scraping.
    """
    results = []
    backends_to_try = ["brave", "yahoo", "yandex"]
    
    for backend in backends_to_try:
        try:
            with DDGS() as ddgs:
                # Prefer fresh results when DDGS supports time filters.
                try:
                    search_iter = ddgs.text(query, max_results=max_results, timelimit="m", backend=backend)
                except TypeError:
                    search_iter = ddgs.text(query, max_results=max_results, backend=backend)

                for r in search_iter:
                    results.append({
                        "title": r.get("title", ""),
                        "href": r.get("href", ""),
                        "body": r.get("body", ""),
                    })
                if results:
                    break
        except Exception as e:
            logger.warning(f"DDG search failed for '{query}' using backend '{backend}': {e}")
            continue

    time.sleep(1.5)  # be polite between calls
    return results


def gather_daily_context(n_queries: int = 4) -> tuple[list[str], str]:
    """
    Runs multiple searches and flattens results into one context blob
    for the LLM prompt. Returns (queries_used, context_text).
    """
    queries = build_daily_queries(n_queries)
    all_snippets = []
    seen_urls = set()

    for q in queries:
        results = search_ddg(q, max_results=8)
        ranked = sorted(results, key=lambda item: _score_result(q, item), reverse=True)

        # Keep strongest matches from each query to avoid noisy context.
        for r in ranked[:5]:
            href = r.get("href", "")
            if href and href in seen_urls:
                continue
            if href:
                seen_urls.add(href)

            source = _detect_source(href)
            score = _score_result(q, r)
            snippet = (
                f"- [source={source} score={score}] {r['title']} "
                f"[URL: {href}]: {r['body'][:350]}"
            )
            all_snippets.append(snippet)

    context_text = "\n".join(all_snippets[:35])  # cap context size
    return queries, context_text
