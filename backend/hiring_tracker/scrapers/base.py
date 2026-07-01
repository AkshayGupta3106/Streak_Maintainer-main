"""
hiring_tracker/scrapers/base.py

Every source-specific scraper (Internshala, Unstop, Amazon, ...) implements
BaseScraper and returns a list of NormalizedListing objects. This is the only
contract the importer (importer.py) cares about - it never knows or cares
whether a listing came from BeautifulSoup-on-HTML, a JSON API, or Playwright.

Adding source #13 later means: subclass BaseScraper, implement run(),
register it in registry.py. Nothing else changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class NormalizedListing:
    company_name: str
    role: str
    opportunity_type: str          # must match hiring_tracker.models.OpportunityType values
    source_name: str                # e.g. "internshala", "unstop"
    source_url: str                 # the specific listing URL, for dedup + "View source"
    career_portal_link: str = ""    # where the student actually applies
    expected_registration_start: Optional[date] = None
    expected_registration_end: Optional[date] = None
    expected_hiring_window_start: Optional[date] = None
    expected_hiring_window_end: Optional[date] = None
    notes: str = ""

    def is_usable(self) -> bool:
        """Minimum bar before we let the importer touch the DB with this."""
        return bool(self.company_name and self.role and self.expected_hiring_window_start)


class BaseScraper(ABC):
    source_name: str = "base"
    # Be a polite scraper: every concrete scraper should sleep this long
    # between requests when paginating. Enforced by http_utils.get(), not here.
    request_delay_seconds: float = 1.5

    @abstractmethod
    def run(self) -> List[NormalizedListing]:
        """Fetch + parse everything this source has and return normalized listings."""
        raise NotImplementedError
