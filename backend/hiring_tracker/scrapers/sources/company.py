import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from datetime import date, timedelta
from typing import List

from hiring_tracker.scrapers.base import BaseScraper, NormalizedListing
from hiring_tracker.scrapers.http_utils import get
from hiring_tracker.scrapers.normalizer import guess_opportunity_type, parse_date_str, is_ai_ml_role

logger = logging.getLogger("hiring_tracker.scrapers.company")

# Generic job keywords to ensure the link text corresponds to a job listing
JOB_ROLE_KEYWORDS = {
    "intern", "internship", "engineer", "analyst", "specialist",
    "developer", "program", "associate", "scientist", "fresher",
    "manager", "lead", "architect", "fellow", "placement", "placements",
    "job", "jobs", "graduate", "grad", "hiring", "recruit", "recruitment",
    "position", "positions"
}


class CompanyCareerScraper(BaseScraper):
    source_name = "company_career"
    request_delay_seconds = 1.5

    def __init__(self, company_name: str, career_url: str):
        super().__init__()
        self.company_name = company_name
        self.career_url = career_url

    def run(self) -> List[NormalizedListing]:
        listings = []
        if not self.career_url:
            return listings

        try:
            logger.info("Running direct career portal fallback scraper for %s at %s", self.company_name, self.career_url)
            resp = get(self.career_url, delay=self.request_delay_seconds)
            soup = BeautifulSoup(resp.text, "html.parser")
            today = date.today()

            # Find all anchor tags
            links = soup.find_all("a", href=True)
            for link in links:
                href = link["href"].strip()
                text = " ".join(link.get_text(strip=True).split())

                if not href or not text:
                    continue

                # 1. Role text must match AI/ML/DS keywords.
                # 2. Role text must also contain general job indicators (e.g. intern, engineer, etc.).
                if not is_ai_ml_role(text):
                    continue

                text_lower = text.lower()
                if not any(kw in text_lower for kw in JOB_ROLE_KEYWORDS):
                    continue

                # Clean and resolve the link to an absolute URL
                job_url = urljoin(self.career_url, href)

                listings.append(NormalizedListing(
                    company_name=self.company_name,
                    role=text,
                    opportunity_type=guess_opportunity_type(text, "FULL_TIME"),
                    source_name=f"{self.company_name.lower()}_fallback",
                    source_url=job_url,
                    career_portal_link=job_url,
                    expected_hiring_window_start=today,
                    expected_hiring_window_end=today + timedelta(days=30),
                    notes=f"Scraped directly from official career portal: {self.career_url}"
                ))

        except Exception as exc:
            logger.warning("Direct career portal fallback failed for %s: %s", self.company_name, exc)

        return listings
