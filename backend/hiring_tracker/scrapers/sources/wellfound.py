import json
import logging
from bs4 import BeautifulSoup
from datetime import date, timedelta
from typing import List

from hiring_tracker.scrapers.base import BaseScraper, NormalizedListing
from hiring_tracker.scrapers.http_utils import get
from hiring_tracker.scrapers.normalizer import guess_opportunity_type, parse_date_str, clean_company_name, is_ai_ml_role

logger = logging.getLogger("hiring_tracker.scrapers.wellfound")


class WellfoundScraper(BaseScraper):
    source_name = "wellfound"
    base_url = "https://wellfound.com"
    request_delay_seconds = 2.5

    ENDPOINTS = [
        "https://wellfound.com/role/l/data-scientist",
        "https://wellfound.com/role/l/machine-learning-engineer",
        "https://wellfound.com/role/l/artificial-intelligence-engineer",
    ]

    def run(self) -> List[NormalizedListing]:
        results = []
        for url in self.ENDPOINTS:
            try:
                results.extend(self._scrape_page(url))
            except Exception as exc:
                logger.warning("Failed to scrape Wellfound %s: %s", url, exc)
        return results

    def _scrape_page(self, url: str) -> List[NormalizedListing]:
        listings = []
        try:
            resp = get(url, delay=self.request_delay_seconds)
            soup = BeautifulSoup(resp.text, "html.parser")

            # 1. Try to find and parse JSON-LD
            ld_scripts = soup.find_all("script", type="application/ld+json")
            today = date.today()

            for script in ld_scripts:
                try:
                    data = json.loads(script.string or "")
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if isinstance(item, dict) and item.get("@type") == "JobPosting":
                            role = item.get("title", "")
                            company = clean_company_name(item.get("hiringOrganization", {}).get("name", ""))
                            job_url = item.get("url") or url

                            if not company or not role:
                                continue
                            if not is_ai_ml_role(role):
                                continue

                            date_posted = parse_date_str(item.get("datePosted", "")) or today
                            deadline = parse_date_str(item.get("validThrough", "")) or (date_posted + timedelta(days=30))

                            listings.append(NormalizedListing(
                                company_name=company,
                                role=role,
                                opportunity_type=guess_opportunity_type(role, "FULL_TIME"),
                                source_name=self.source_name,
                                source_url=job_url,
                                career_portal_link=job_url,
                                expected_hiring_window_start=date_posted,
                                expected_hiring_window_end=deadline,
                            ))
                except Exception as e:
                    logger.debug("Failed parsing JSON-LD script block: %s", e)
                    continue

            # 2. HTML DOM parsing fallback
            if not listings:
                cards = soup.select(".styles_component__2-y0a") or soup.select(".styles_jobCard__2_U6K") or soup.select("[data-test='JobResult']")
                for card in cards:
                    try:
                        role_tag = card.select_one("h3") or card.select_one("a.styles_title__3V04a")
                        company_tag = card.select_one(".styles_companyName__2PZ2m") or card.select_one("h4")
                        link_tag = card.select_one("a[href*='/jobs/']") or card.select_one("a")

                        role = role_tag.get_text(strip=True) if role_tag else ""
                        company = clean_company_name(company_tag.get_text(strip=True) if company_tag else "")
                        href = link_tag["href"] if link_tag and link_tag.has_attr("href") else ""
                        job_url = href if href.startswith("http") else f"{self.base_url}{href}"

                        if not company or not role:
                            continue
                        if not is_ai_ml_role(role):
                            continue

                        listings.append(NormalizedListing(
                            company_name=company,
                            role=role,
                            opportunity_type=guess_opportunity_type(role, "FULL_TIME"),
                            source_name=self.source_name,
                            source_url=job_url,
                            career_portal_link=job_url,
                            expected_hiring_window_start=today,
                            expected_hiring_window_end=today + timedelta(days=30),
                        ))
                    except Exception as e:
                        logger.debug("Error parsing HTML job card: %s", e)
                        continue

        except Exception as exc:
            logger.warning("Error fetching/parsing page %s: %s", url, exc)

        return listings
