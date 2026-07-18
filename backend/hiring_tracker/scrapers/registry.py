"""
hiring_tracker/scrapers/registry.py

Single place to register/deregister scrapers.
ScrapeView (api/views.py) calls get_all_scrapers() to know what exists.
Add a new source: import it and append to _SCRAPERS.
"""

from typing import List
from hiring_tracker.scrapers.base import BaseScraper
from hiring_tracker.scrapers.sources.internshala import InternshalaScraper
from hiring_tracker.scrapers.sources.wellfound import WellfoundScraper
from hiring_tracker.scrapers.sources.hirist import HiristScraper
from hiring_tracker.scrapers.sources.cutshort import CutshortScraper
from hiring_tracker.scrapers.sources.unstop import UnstopScraper

_SCRAPERS: List[BaseScraper] = [
    InternshalaScraper(),
    WellfoundScraper(),
    HiristScraper(),
    CutshortScraper(),
    UnstopScraper(),
]


def get_all_scrapers() -> List[BaseScraper]:
    return list(_SCRAPERS)

