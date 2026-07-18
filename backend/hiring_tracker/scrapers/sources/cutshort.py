import json
import logging
from bs4 import BeautifulSoup
from datetime import date, timedelta
from typing import List

from hiring_tracker.scrapers.base import BaseScraper, NormalizedListing
from hiring_tracker.scrapers.http_utils import get
from hiring_tracker.scrapers.normalizer import guess_opportunity_type, parse_date_str, clean_company_name, is_ai_ml_role

logger = logging.getLogger("hiring_tracker.scrapers.cutshort")


class CutshortScraper(BaseScraper):
    source_name = "cutshort"
    base_url = "https://cutshort.io"
    request_delay_seconds = 2.0

    ENDPOINTS = [
        "https://cutshort.io/jobs/data-scientist-jobs",
        "https://cutshort.io/jobs/machine-learning-jobs",
    ]

    def run(self) -> List[NormalizedListing]:
        results = []
        for url in self.ENDPOINTS:
            try:
                results.extend(self._scrape_page(url))
            except Exception as exc:
                logger.warning("Failed to scrape Cutshort %s: %s", url, exc)
        return results

    def _scrape_page(self, url: str) -> List[NormalizedListing]:
        listings = []
        try:
            resp = get(url, delay=self.request_delay_seconds)
            soup = BeautifulSoup(resp.text, "html.parser")

            # 1. JSON-LD parsing
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

            # 2. Fallback HTML DOM selectors
            if not listings:
                cards = soup.select(".job-card") or soup.select(".job-list-card") or soup.select("div[class*='JobCard']")
                for card in cards:
                    try:
                        role_tag = card.select_one(".job-title") or card.select_one("h3") or card.select_one("a[href*='/job/']")
                        company_tag = card.select_one(".company-name") or card.select_one("h4") or card.select_one(".company")
                        link_tag = card.select_one("a[href*='/job/']") or card.select_one("a")

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
