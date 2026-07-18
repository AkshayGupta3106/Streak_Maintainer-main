"""
hiring_tracker/scrapers/normalizer.py

Listing pages phrase dates and types in a dozen inconsistent ways
("Apply by 15 Aug", "Closes in 3 days", "Internship", "Full Time").
Each source scraper should funnel raw strings through these helpers
instead of writing its own ad-hoc parsing, so a fix here fixes every
source at once.
"""

import re
from datetime import date, datetime, timedelta
from typing import Optional

from hiring_tracker.models import OpportunityType

_TYPE_KEYWORDS = [
    (OpportunityType.INTERNSHIP, ["intern", "summer intern", "step"]),
    (OpportunityType.HACKATHON, ["hackathon", "hack-a-thon", "coding challenge"]),
    (OpportunityType.OA, ["online assessment", " oa ", "nqt"]),
    (OpportunityType.GRAD_PROGRAM, ["graduate program", "analyst program", "leadership program"]),
    (OpportunityType.FULL_TIME, ["full time", "full-time", "fresher", "associate engineer"]),
]

_DATE_PATTERNS = [
    "%d %b %Y",      # 15 Aug 2026
    "%d %B %Y",      # 15 August 2026
    "%d-%m-%Y",       # 15-08-2026
    "%d/%m/%Y",       # 15/08/2026
    "%b %d, %Y",      # Aug 15, 2026
    "%B %d, %Y",      # August 15, 2026
    "%Y-%m-%d",       # 2026-08-15
]

_RELATIVE_DAYS_RE = re.compile(r"(\d+)\s*day", re.IGNORECASE)
_RELATIVE_WEEKS_RE = re.compile(r"(\d+)\s*week", re.IGNORECASE)
_RELATIVE_MONTHS_RE = re.compile(r"(\d+)\s*month", re.IGNORECASE)


def guess_opportunity_type(*texts: str) -> str:
    """Looks at title/role/description text and guesses the OpportunityType."""
    combined = " ".join(t.lower() for t in texts if t)
    for opp_type, keywords in _TYPE_KEYWORDS:
        if any(kw in combined for kw in keywords):
            return opp_type
    return OpportunityType.FULL_TIME  # safest default for off-campus drives


def parse_date_str(raw: str, today: Optional[date] = None) -> Optional[date]:
    """
    Best-effort parse of a date string into a date object.
    Handles absolute formats ("15 Aug 2026") and relative phrases
    ("Closes in 5 days", "in 2 weeks", "in 1 month").
    Returns None if nothing could be parsed - callers must handle that,
    never silently default to today's date.
    """
    if not raw:
        return None

    raw = raw.strip()
    today = today or date.today()

    for fmt in _DATE_PATTERNS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue

    days_match = _RELATIVE_DAYS_RE.search(raw)
    if days_match:
        return today + timedelta(days=int(days_match.group(1)))

    weeks_match = _RELATIVE_WEEKS_RE.search(raw)
    if weeks_match:
        return today + timedelta(weeks=int(weeks_match.group(1)))

    months_match = _RELATIVE_MONTHS_RE.search(raw)
    if months_match:
        return today + timedelta(days=int(months_match.group(1)) * 30)

    if "today" in raw.lower():
        return today
    if "tomorrow" in raw.lower():
        return today + timedelta(days=1)

    return None


def clean_company_name(raw: str) -> str:
    """Strip common suffixes/noise so 'TCS Pvt. Ltd.' matches Company 'TCS'."""
    raw = re.sub(r"\s+", " ", raw or "").strip()
    raw = re.sub(
        r"\b(pvt\.?|private|ltd\.?|limited|inc\.?|llp|corp\.?|corporation)\b\.?",
        "",
        raw,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", raw).strip(" .,-")


ROLE_HINT_RE = re.compile(
    r"(data\s*science|data\s*scientist|machine\s*learning|ml\s*engineer|ai\s*engineer|genai|nlp|computer\s*vision|artificial\s*intelligence|deep\s*learning|llm)",
    re.IGNORECASE,
)


def is_ai_ml_role(role_name: str) -> bool:
    """Returns True if the role name contains AI/ML/Data Science keywords."""
    return bool(ROLE_HINT_RE.search(role_name))

