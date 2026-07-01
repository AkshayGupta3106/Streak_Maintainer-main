"""
hiring_tracker/scrapers/registry.py

Single place to register/deregister scrapers.
ScrapeView (api/views.py) calls get_all_scrapers() to know what exists.
Add a new source: import it and append to _SCRAPERS.
"""

from typing import List
from hiring_tracker.scrapers.base import BaseScraper

# Import individual scrapers here as section 2 scrapers are completed.
# They're referenced lazily so a broken single scraper doesn't prevent
# the rest from running.
from hiring_tracker.scrapers.sources.internshala import IntershalaScraper
from hiring_tracker.scrapers.sources.unstop import UnstopScraper
from hiring_tracker.scrapers.sources.freshersworld import FreshersWorldScraper
from hiring_tracker.scrapers.sources.gfg import GFGScraper
from hiring_tracker.scrapers.sources.ambitionbox import AmbitionBoxScraper
from hiring_tracker.scrapers.sources.lets_code import LetsCodeScraper
from hiring_tracker.scrapers.sources.tcs import TCSCareerScraper
from hiring_tracker.scrapers.sources.infosys import InfosysCareerScraper
from hiring_tracker.scrapers.sources.microsoft import MicrosoftCareerScraper
from hiring_tracker.scrapers.sources.amazon import AmazonCareerScraper
from hiring_tracker.scrapers.sources.google import GoogleCareerScraper
from hiring_tracker.scrapers.sources.goldman import GoldmanCareerScraper

_SCRAPERS: List[BaseScraper] = [
    IntershalaScraper(),
    UnstopScraper(),
    FreshersWorldScraper(),
    GFGScraper(),
    AmbitionBoxScraper(),
    LetsCodeScraper(),
    TCSCareerScraper(),
    InfosysCareerScraper(),
    MicrosoftCareerScraper(),
    AmazonCareerScraper(),
    GoogleCareerScraper(),
    GoldmanCareerScraper(),
]


def get_all_scrapers() -> List[BaseScraper]:
    return list(_SCRAPERS)
