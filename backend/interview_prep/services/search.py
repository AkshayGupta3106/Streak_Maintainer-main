"""
Pulls recent signal on what's actually being asked in AI/DS interviews.
Uses ddgs (DuckDuckGo search wrapper) — no API key required.
"""
import logging
import random
import time
from ddgs import DDGS

logger = logging.getLogger(__name__)

# Rotate companies/topics so you don't get the same search results every day
COMPANIES = ["Google", "Meta", "Amazon", "Microsoft", "OpenAI", "Anthropic",
             "Netflix", "startup GenAI", "Nvidia", "Stripe"]

TOPIC_TEMPLATES = [
    "AI engineer interview questions {company} 2026",
    "data scientist interview questions {company} recent",
    "machine learning system design interview {company}",
    "LLM GenAI interview questions asked {company}",
    "statistics probability interview questions data science {company}",
]


def build_daily_queries(n_queries: int = 4) -> list[str]:
    """Pick a rotating subset of query templates for today's run."""
    companies = random.sample(COMPANIES, k=min(n_queries, len(COMPANIES)))
    templates = random.sample(TOPIC_TEMPLATES, k=min(n_queries, len(TOPIC_TEMPLATES)))
    queries = [t.format(company=c) for t, c in zip(templates, companies)]
    return queries


def search_ddg(query: str, max_results: int = 5) -> list[dict]:
    """
    Returns list of {title, href, body} dicts.
    Rate-limit yourself — DDG will block aggressive scraping.
    """
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "body": r.get("body", ""),
                })
    except Exception as e:
        logger.warning(f"DDG search failed for '{query}': {e}")
    time.sleep(1.5)  # be polite between calls
    return results


def gather_daily_context(n_queries: int = 4) -> tuple[list[str], str]:
    """
    Runs multiple searches and flattens results into one context blob
    for the LLM prompt. Returns (queries_used, context_text).
    """
    queries = build_daily_queries(n_queries)
    all_snippets = []

    for q in queries:
        results = search_ddg(q)
        for r in results:
            snippet = f"- {r['title']}: {r['body'][:250]}"
            all_snippets.append(snippet)

    context_text = "\n".join(all_snippets[:30])  # cap context size
    return queries, context_text
