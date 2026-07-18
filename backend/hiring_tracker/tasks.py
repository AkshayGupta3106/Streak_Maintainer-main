import logging
from celery import shared_task
from django.db.models import Q

from hiring_tracker.models import Company
from hiring_tracker.scrapers.registry import get_all_scrapers
from hiring_tracker.scrapers.importer import import_listings, _find_company
from hiring_tracker.scrapers.sources.company import CompanyCareerScraper

logger = logging.getLogger("hiring_tracker.tasks")


@shared_task
def run_platform_first_scrapers(requested_sources=None):
    """
    Orchestrates the platform-first scraping workflow:
    1. Run platform scrapers (Internshala, Wellfound, Hirist, Cutshort, Unstop).
    2. Collect and normalize listings.
    3. Match Listings to active companies in the DB to find which companies had NO platform listings.
    4. For unmatched active companies, trigger fallback direct career portal scraper.
    5. Import and merge all listings into the database.
    """
    logger.info("Starting platform-first job scraping task...")

    # 1. Fetch registered platform scrapers
    all_scrapers = get_all_scrapers()

    if requested_sources:
        scrapers = [s for s in all_scrapers if s.source_name in requested_sources]
    else:
        scrapers = all_scrapers

    logger.info("Executing platform scrapers: %s", [s.source_name for s in scrapers])

    platform_listings = []
    for scraper in scrapers:
        try:
            logger.info("Running scraper: %s", scraper.source_name)
            listings = scraper.run()
            platform_listings.extend(listings)
            logger.info("Scraper %s found %d raw listings", scraper.source_name, len(listings))
        except Exception as exc:
            logger.exception("Scraper %s failed", scraper.source_name)

    # 2. Identify active companies matched by platform listings
    matched_company_ids = set()
    for listing in platform_listings:
        matched_comp = _find_company(listing.company_name)
        if matched_comp:
            matched_company_ids.add(matched_comp.id)

    # 3. For any active company with 0 matched listings, run direct career page crawler as fallback
    active_companies = Company.objects.filter(is_active=True)
    fallback_listings = []

    logger.info("Active companies in database: %d. Found on platforms: %d", active_companies.count(), len(matched_company_ids))

    for company in active_companies:
        if company.id not in matched_company_ids:
            if company.career_portal_base_url:
                logger.info("Company '%s' has 0 platform listings. Falling back to direct URL: %s", company.name, company.career_portal_base_url)
                try:
                    fallback_scraper = CompanyCareerScraper(company.name, company.career_portal_base_url)
                    listings = fallback_scraper.run()
                    fallback_listings.extend(listings)
                    logger.info("Fallback scraper for %s found %d listings", company.name, len(listings))
                except Exception as exc:
                    logger.exception("Direct career portal fallback failed for %s", company.name)
            else:
                logger.debug("Company '%s' has 0 platform listings but no career portal URL configured. Skipping fallback.", company.name)

    # 4. Import all listings
    all_listings = platform_listings + fallback_listings
    logger.info("Total listings gathered (platform: %d, fallback: %d). Importing...", len(platform_listings), len(fallback_listings))

    stats = import_listings(all_listings)
    logger.info("Scrape and import completed successfully: %s", stats.summary())

    return {
        "status": "success",
        "seen": stats.seen,
        "created": stats.created,
        "updated": stats.updated,
        "skipped_unusable": stats.skipped_unusable,
        "skipped_unknown_company": stats.skipped_unknown_company,
        "auto_created_company": stats.auto_created_company,
    }
