"""
Search-backed scrapers for additional opportunity websites.

These scrapers use site-restricted DuckDuckGo queries to discover fresh
AI/ML/Data Science internship and entry-level opportunities (including 2027
batch oriented posts), then normalize them into NormalizedListing records.

Why this approach:
- Many job boards change HTML markup often or serve dynamic pages.
- Search results provide a stable discovery layer across many sources.
- Each site still appears as an independent scraper source in API output.
"""

from __future__ import annotations

import logging
import os
import random
import re
import time
from datetime import date, timedelta
from typing import Iterable, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from ddgs import DDGS
import requests

from hiring_tracker.models import OpportunityType
from hiring_tracker.scrapers.base import BaseScraper, NormalizedListing
from hiring_tracker.scrapers.normalizer import clean_company_name, guess_opportunity_type, parse_date_str

logger = logging.getLogger("hiring_tracker.scrapers.search_backed")

TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "source",
}


def _canonicalize_url(raw_url: str) -> str:
    if not raw_url:
        return ""
    try:
        parsed = urlparse(raw_url.strip())
        cleaned_query = [
            (k, v)
            for (k, v) in parse_qsl(parsed.query, keep_blank_values=True)
            if k and k.lower() not in TRACKING_QUERY_KEYS and not k.lower().startswith(TRACKING_QUERY_PREFIXES)
        ]
        normalized_path = parsed.path.rstrip("/") or "/"
        return urlunparse(
            parsed._replace(
                path=normalized_path,
                query=urlencode(cleaned_query, doseq=True),
                fragment="",
            )
        )
    except Exception:
        return raw_url.strip()


ROLE_HINT_RE = re.compile(
    r"(data\s*science|data\s*scientist|machine\s*learning|ml\s*engineer|ai\s*engineer|genai|nlp|computer\s*vision)",
    re.IGNORECASE,
)


def _contains_target_keywords(text: str) -> bool:
    lowered = (text or "").lower()
    return any(
        token in lowered
        for token in [
            "intern",
            "internship",
            "fresher",
            "entry level",
            "new grad",
            "batch 2027",
            "batch of 2027",
            "graduate",
            "campus",
            "placement",
            "hiring",
            "apply",
        ]
    ) and bool(ROLE_HINT_RE.search(lowered))


def _extract_company(title: str, body: str, fallback: str) -> str:
    text = f"{title} {body}".strip()

    patterns = [
        r"\b(?:at|with|for)\s+([A-Z][A-Za-z0-9&.,'()\-\s]{1,60})",
        r"^([A-Z][A-Za-z0-9&.,'()\-\s]{1,40})\s*[\-:|]",
    ]

    for pat in patterns:
        m = re.search(pat, text)
        if m:
            candidate = clean_company_name(m.group(1))
            if len(candidate) >= 2:
                return candidate

    return fallback


def _extract_role(title: str, body: str) -> Optional[str]:
    merged = f"{title} {body}".strip()

    role_patterns = [
        r"((?:Data\s*Science|Data\s*Scientist|Machine\s*Learning|ML|AI|GenAI|NLP|Computer\s*Vision)[^|,:\-]{0,60}(?:Intern|Engineer|Analyst|Associate|Trainee))",
        r"((?:Internship|Intern|Engineer|Analyst|Associate|Trainee)[^|,:\-]{0,50}(?:Data\s*Science|Machine\s*Learning|AI|ML|GenAI|NLP|Computer\s*Vision))",
    ]

    for pat in role_patterns:
        m = re.search(pat, merged, flags=re.IGNORECASE)
        if m:
            role = re.sub(r"\s+", " ", m.group(1)).strip(" -|:,")
            if len(role) >= 6:
                return role

    if ROLE_HINT_RE.search(merged):
        return title.strip()[:180] if title.strip() else None

    return None


class DDGSiteSearchScraper(BaseScraper):
    source_name = "ddg_site_base"
    domain = ""
    request_delay_seconds = 2.0
    fallback_company_name = "Unknown"
    max_search_retries = 3
    base_backoff_seconds = 2.0
    # Free-provider first strategy. SearXNG is free (no paid key required).
    # DDG fallback remains opt-in only.
    default_provider_order = ("searxng",)

    QUERY_TEMPLATES = [
        'site:{domain} ("data science" OR "machine learning" OR "ai engineer" OR "ml engineer") (internship OR intern OR fresher OR "entry level" OR "new grad") (2027 OR "batch 2027" OR "batch of 2027")',
        'site:{domain} ("data scientist" OR "ai engineer" OR "ml engineer") ("campus hiring" OR placement OR graduate OR trainee) (internship OR jobs)',
        'site:{domain} ("genai" OR "llm" OR "nlp" OR "computer vision") (intern OR fresher OR "entry level")',
    ]

    def _queries(self) -> Iterable[str]:
        for template in self.QUERY_TEMPLATES:
            yield template.format(domain=self.domain)

    def _is_dgg_allowed(self) -> bool:
        return os.getenv("ALLOW_DDG_FALLBACK", "false").strip().lower() in {"1", "true", "yes", "on"}

    def _provider_order(self) -> list[str]:
        configured = os.getenv("SEARCH_PROVIDER_ORDER", "").strip()
        if configured:
            parsed = [part.strip().lower() for part in configured.split(",") if part.strip()]
            if parsed:
                return parsed

        order = list(self.default_provider_order)
        if self._is_dgg_allowed():
            order.append("ddg")
        return order

    def _has_active_provider(self) -> bool:
        for provider in self._provider_order():
            if provider == "searxng":
                return True
            if provider == "ddg":
                return True
        return False

    def _normalize_rows(self, rows: list[dict]) -> list[dict]:
        normalized: list[dict] = []
        for r in rows:
            normalized.append(
                {
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "body": r.get("body", ""),
                }
            )
        return normalized

    def _search_ddg(self, query: str) -> list[dict]:
        rows = []
        with DDGS() as ddgs:
            try:
                items = ddgs.text(query, max_results=10, timelimit="m")
            except TypeError:
                items = ddgs.text(query, max_results=10)

            for r in items:
                rows.append(
                    {
                        "title": r.get("title", ""),
                        "href": r.get("href", ""),
                        "body": r.get("body", ""),
                    }
                )
        return self._normalize_rows(rows)

    def _searxng_instances(self) -> list[str]:
        configured = os.getenv("SEARXNG_BASE_URLS", "").strip()
        if configured:
            return [u.strip().rstrip("/") for u in configured.split(",") if u.strip()]

        return [
            "https://searx.be",
            "https://search.sapti.me",
        ]

    def _search_searxng(self, query: str) -> list[dict]:
        last_error = None
        for base_url in self._searxng_instances():
            try:
                response = requests.get(
                    f"{base_url}/search",
                    params={
                        "q": query,
                        "format": "json",
                        "language": "en",
                    },
                    headers={
                        "User-Agent": "StreakMaintainerBot/1.0",
                        "Accept": "application/json",
                    },
                    timeout=20,
                )
                response.raise_for_status()
                payload = response.json() or {}
                rows = []
                for item in payload.get("results", [])[:10]:
                    rows.append(
                        {
                            "title": item.get("title", ""),
                            "href": item.get("url", ""),
                            "body": item.get("content", ""),
                        }
                    )
                if rows:
                    return self._normalize_rows(rows)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "[%s] SearXNG instance failed (%s) for query '%s': %s",
                    self.source_name,
                    base_url,
                    query,
                    exc,
                )
                continue

        if last_error:
            raise last_error

        return []

    def _search(self, query: str) -> list[dict]:
        last_error = None
        attempted = []

        for provider in self._provider_order():
            if provider == "searxng":
                attempted.append("searxng")
                try:
                    rows = self._search_searxng(query)
                    if rows:
                        logger.info("[%s] Using SearXNG results for query '%s'", self.source_name, query)
                        return rows
                except Exception as exc:
                    last_error = exc
                    logger.warning("[%s] SearXNG search failed for query '%s': %s", self.source_name, query, exc)
                continue

            if provider == "ddg":
                attempted.append("ddg")
                for attempt in range(1, self.max_search_retries + 1):
                    try:
                        rows = self._search_ddg(query)
                        if rows:
                            if attempt > 1:
                                logger.info("[%s] DDG recovered on attempt %s for query '%s'", self.source_name, attempt, query)
                            return rows
                        logger.info("[%s] DDG returned no rows for query '%s'", self.source_name, query)
                        break
                    except Exception as exc:
                        last_error = exc
                        delay = self.base_backoff_seconds * (2 ** (attempt - 1)) + random.uniform(0.1, 0.8)
                        logger.warning(
                            "[%s] DDG attempt %s/%s failed for query '%s': %s. Retrying in %.1fs",
                            self.source_name,
                            attempt,
                            self.max_search_retries,
                            query,
                            exc,
                            delay,
                        )
                        if attempt < self.max_search_retries:
                            time.sleep(delay)
                continue

        if not attempted:
            logger.warning(
                "[%s] No search provider configured for query '%s'. Configure SEARXNG_BASE_URLS or "
                "DDG is disabled by default; enable only by setting ALLOW_DDG_FALLBACK=true.",
                self.source_name,
                query,
            )
            return []

        if last_error:
            logger.warning("[%s] Search failed for query '%s': %s", self.source_name, query, last_error)
        else:
            logger.info("[%s] Search completed with no results for query '%s' using providers=%s", self.source_name, query, attempted)
        return []

    def run(self) -> List[NormalizedListing]:
        if not self._has_active_provider():
            logger.warning(
                "[%s] Skipping source: no active search provider. Configure SEARXNG_BASE_URLS, "
                "or enable DDG fallback explicitly.",
                self.source_name,
            )
            return []

        today = date.today()
        seen_urls = set()
        listings: List[NormalizedListing] = []

        for query in self._queries():
            for row in self._search(query):
                title = row.get("title", "")
                body = row.get("body", "")
                href = _canonicalize_url(row.get("href", ""))

                if not href or href in seen_urls:
                    continue
                seen_urls.add(href)

                merged = f"{title} {body}".strip()
                if not _contains_target_keywords(merged):
                    continue

                role = _extract_role(title, body)
                if not role:
                    continue

                company = _extract_company(title, body, self.fallback_company_name)
                if not company:
                    continue

                dt = parse_date_str(body) or parse_date_str(title)
                window_start = dt or (today + timedelta(days=45))
                window_end = window_start + timedelta(days=30)

                listings.append(
                    NormalizedListing(
                        company_name=company,
                        role=role,
                        opportunity_type=guess_opportunity_type(merged, OpportunityType.INTERNSHIP),
                        source_name=self.source_name,
                        source_url=href,
                        career_portal_link=href,
                        expected_hiring_window_start=window_start,
                        expected_hiring_window_end=window_end,
                        notes=(
                            "Discovered via site-scoped web search for AI/DS internship "
                            "and entry-level opportunities oriented to 2027 batch."
                        ),
                    )
                )

            time.sleep(self.request_delay_seconds + random.uniform(0.1, 0.5))

        return listings


class UnstopSearchScraper(DDGSiteSearchScraper):
    source_name = "unstop_search"
    domain = "unstop.com"
    fallback_company_name = "Unstop Listing"


class SupersetSearchScraper(DDGSiteSearchScraper):
    source_name = "superset_search"
    domain = "joinsuperset.com"
    fallback_company_name = "Superset Listing"


class NaukriSearchScraper(DDGSiteSearchScraper):
    source_name = "naukri_search"
    domain = "naukri.com"
    fallback_company_name = "Naukri Listing"


class FounditSearchScraper(DDGSiteSearchScraper):
    source_name = "foundit_search"
    domain = "foundit.in"
    fallback_company_name = "Foundit Listing"


class InstahyreSearchScraper(DDGSiteSearchScraper):
    source_name = "instahyre_search"
    domain = "instahyre.com"
    fallback_company_name = "Instahyre Listing"


class HiristSearchScraper(DDGSiteSearchScraper):
    source_name = "hirist_search"
    domain = "hirist.tech"
    fallback_company_name = "Hirist Listing"


class CutshortSearchScraper(DDGSiteSearchScraper):
    source_name = "cutshort_search"
    domain = "cutshort.io"
    fallback_company_name = "Cutshort Listing"


class AICTEInternshipPortalSearchScraper(DDGSiteSearchScraper):
    source_name = "aicte_internship_portal_search"
    domain = "internship.aicte-india.org"
    fallback_company_name = "AICTE Internship Portal Listing"


class AnalyticsVidhyaJobsSearchScraper(DDGSiteSearchScraper):
    source_name = "analytics_vidhya_jobs_search"
    domain = "analyticsvidhya.com/jobs"
    fallback_company_name = "Analytics Vidhya Jobs Listing"


class NVIDIAIndiaCareersSearchScraper(DDGSiteSearchScraper):
    source_name = "nvidia_india_careers_search"
    domain = "nvidia.com/en-in"
    fallback_company_name = "NVIDIA India Careers Listing"


class MicrosoftIndiaCareersSearchScraper(DDGSiteSearchScraper):
    source_name = "microsoft_india_careers_search"
    domain = "careers.microsoft.com"
    fallback_company_name = "Microsoft India Careers Listing"


class GoogleCareersSearchScraper(DDGSiteSearchScraper):
    source_name = "google_careers_search"
    domain = "careers.google.com"
    fallback_company_name = "Google Careers Listing"


class AtlassianCareersSearchScraper(DDGSiteSearchScraper):
    source_name = "atlassian_careers_search"
    domain = "atlassian.com/careers"
    fallback_company_name = "Atlassian Careers Listing"


class OracleCareersSearchScraper(DDGSiteSearchScraper):
    source_name = "oracle_careers_search"
    domain = "oracle.com/careers"
    fallback_company_name = "Oracle Careers Listing"


class AdobeCareersSearchScraper(DDGSiteSearchScraper):
    source_name = "adobe_careers_search"
    domain = "adobe.com/careers"
    fallback_company_name = "Adobe Careers Listing"


class SamsungResearchIndiaCareersSearchScraper(DDGSiteSearchScraper):
    source_name = "samsung_research_india_careers_search"
    domain = "research.samsung.com"
    fallback_company_name = "Samsung Research India Careers Listing"


class FlipkartCareersSearchScraper(DDGSiteSearchScraper):
    source_name = "flipkart_careers_search"
    domain = "flipkartcareers.com"
    fallback_company_name = "Flipkart Careers Listing"


class PhonePeCareersSearchScraper(DDGSiteSearchScraper):
    source_name = "phonepe_careers_search"
    domain = "phonepe.com/careers"
    fallback_company_name = "PhonePe Careers Listing"
