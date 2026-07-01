"""
hiring_tracker/scrapers/sources/internshala.py

Source: internshala
Note: Server-rendered. No JS needed. Cheerio-style bs4 parsing.
"""

import logging
from datetime import date, timedelta
from typing import List

from bs4 import BeautifulSoup

from hiring_tracker.scrapers.base import BaseScraper, NormalizedListing
from hiring_tracker.scrapers.http_utils import get
from hiring_tracker.scrapers.normalizer import guess_opportunity_type, parse_date_str, clean_company_name

logger = logging.getLogger("hiring_tracker.scrapers.internshala")


class IntershalaScraper(BaseScraper):
    source_name = "internshala"
    base_url = "https://internshala.com"
    request_delay_seconds = 2.0

    ENDPOINTS = [('https://internshala.com/internships/computer-science-internship/', 'INTERNSHIP'), ('https://internshala.com/jobs/computer-science-jobs/', 'FULL_TIME')]

    # -------------------------------------------------------------------------
    # SELECTOR NOTE: Selectors below are based on the site structure at build
    # time. If this scraper starts returning 0 results, inspect the live page
    # DOM and update the selector constants here - the run() logic itself
    # won't need to change.
    # -------------------------------------------------------------------------
    LIST_SEL = "div.individual_internship"
    COMPANY_SEL = ".company_name h4"
    ROLE_SEL = ".profile h3"
    LOCATION_SEL = ".location_link"
    DEADLINE_SEL = ".application-ends span"
    LINK_SEL = "a.view_detail_button"

    def run(self) -> List[NormalizedListing]:
        results = []
        for url, default_type in self.ENDPOINTS:
            try:
                results.extend(self._scrape_page(url, default_type))
            except Exception as exc:
                logger.warning("Failed to scrape %s: %s", url, exc)
        return results

    def _scrape_page(self, url: str, default_type: str) -> List[NormalizedListing]:
        
        resp = get(url, delay=self.request_delay_seconds)
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select(self.LIST_SEL) if self.LIST_SEL else []
        if not cards:
            logger.warning("[%s] 0 cards found at %s — selector may need updating", self.source_name, url)
        listings = []
        today = date.today()
        for card in cards:
            try:
                company_tag = card.select_one(self.COMPANY_SEL) if hasattr(self, "COMPANY_SEL") else None
                role_tag = card.select_one(self.ROLE_SEL) if hasattr(self, "ROLE_SEL") else None
                link_tag = card.select_one(self.LINK_SEL) if hasattr(self, "LINK_SEL") else None
                deadline_tag = card.select_one(self.DEADLINE_SEL) if hasattr(self, "DEADLINE_SEL") else None

                company = clean_company_name(company_tag.get_text(strip=True) if company_tag else "")
                role = role_tag.get_text(strip=True) if role_tag else ""
                href = link_tag["href"] if link_tag and link_tag.has_attr("href") else ""
                source_url = href if href.startswith("http") else f"{self.base_url}{href}"
                deadline_raw = deadline_tag.get_text(strip=True) if deadline_tag else ""

                if not company or not role:
                    continue

                window_start = parse_date_str(deadline_raw) or today + timedelta(days=30)
                window_end = window_start + timedelta(days=30)

                listings.append(NormalizedListing(
                    company_name=company,
                    role=role,
                    opportunity_type=guess_opportunity_type(role, default_type),
                    source_name=self.source_name,
                    source_url=source_url,
                    career_portal_link=source_url,
                    expected_hiring_window_start=window_start,
                    expected_hiring_window_end=window_end,
                ))
            except Exception as exc:
                logger.debug("Error parsing card: %s", exc)
                continue
        return listings

