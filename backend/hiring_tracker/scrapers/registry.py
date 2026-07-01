"""
hiring_tracker/scrapers/registry.py

Single place to register/deregister scrapers.
ScrapeView (api/views.py) calls get_all_scrapers() to know what exists.
Add a new source: import it and append to _SCRAPERS.
"""

from typing import List
from hiring_tracker.scrapers.base import BaseScraper
from hiring_tracker.scrapers.sources.internshala import IntershalaScraper
from hiring_tracker.scrapers.sources.search_backed import (
    AICTEInternshipPortalSearchScraper,
    AdobeCareersSearchScraper,
    AnalyticsVidhyaJobsSearchScraper,
    AtlassianCareersSearchScraper,
    CutshortSearchScraper,
    FlipkartCareersSearchScraper,
    FounditSearchScraper,
    GoogleCareersSearchScraper,
    HiristSearchScraper,
    InstahyreSearchScraper,
    MicrosoftIndiaCareersSearchScraper,
    NaukriSearchScraper,
    NVIDIAIndiaCareersSearchScraper,
    OracleCareersSearchScraper,
    PhonePeCareersSearchScraper,
    SamsungResearchIndiaCareersSearchScraper,
    SupersetSearchScraper,
    UnstopSearchScraper,
)

_SCRAPERS: List[BaseScraper] = [
    IntershalaScraper(),
    UnstopSearchScraper(),
    SupersetSearchScraper(),
    CutshortSearchScraper(),
    InstahyreSearchScraper(),
    HiristSearchScraper(),
    NaukriSearchScraper(),
    FounditSearchScraper(),
    AICTEInternshipPortalSearchScraper(),
    AnalyticsVidhyaJobsSearchScraper(),
    NVIDIAIndiaCareersSearchScraper(),
    MicrosoftIndiaCareersSearchScraper(),
    GoogleCareersSearchScraper(),
    AtlassianCareersSearchScraper(),
    OracleCareersSearchScraper(),
    AdobeCareersSearchScraper(),
    SamsungResearchIndiaCareersSearchScraper(),
    FlipkartCareersSearchScraper(),
    PhonePeCareersSearchScraper(),
]


def get_all_scrapers() -> List[BaseScraper]:
    return list(_SCRAPERS)
