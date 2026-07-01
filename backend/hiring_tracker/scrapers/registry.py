"""
hiring_tracker/scrapers/registry.py

Single place to register/deregister scrapers.
ScrapeView (api/views.py) calls get_all_scrapers() to know what exists.
Add a new source: import it and append to _SCRAPERS.
"""

from typing import List
from hiring_tracker.scrapers.base import BaseScraper
from hiring_tracker.scrapers.sources.internshala import IntershalaScraper

_SCRAPERS: List[BaseScraper] = [
    IntershalaScraper(),
]


def get_all_scrapers() -> List[BaseScraper]:
    return list(_SCRAPERS)
