"""
hiring_tracker/scrapers/importer.py

This is the "scraper/import engine" from the product spec - the single
chokepoint every source funnels through before touching the database.
Keeping this separate from the scrapers themselves means a new source
never needs to know about Company matching, dedup, or which fields are
safe to overwrite vs. preserve.

Matching rules:
  - Company is matched case-insensitively against existing Company rows
    (with suffix stripping via normalizer.clean_company_name). New
    companies are NOT auto-created - an unrecognised company name is
    logged and skipped, so a scraper mis-parsing "View Company" as a
    name doesn't pollute the table. Add it via the admin/seed first.
  - An Opportunity is considered "the same listing" if it matches on
    (company, role, source_url) OR (company, role, overlapping hiring
    window) - covers both "we re-scraped the same URL" and "two
    different aggregators listing the same drive".
  - Scraped data always wins over seeded/projected data for date
    fields, since it's closer to the source of truth. Manual edits
    (source=MANUAL) are never overwritten by the importer.
"""

import logging
from dataclasses import dataclass
from typing import List

from django.db.models import Q

from hiring_tracker.models import Company, Opportunity, OpportunityStatus, SourceType
from hiring_tracker.scrapers.base import NormalizedListing
from hiring_tracker.scrapers.normalizer import clean_company_name

logger = logging.getLogger("hiring_tracker.scrapers")


@dataclass
class ImportStats:
    seen: int = 0
    skipped_unusable: int = 0
    skipped_unknown_company: int = 0
    created: int = 0
    updated: int = 0
    skipped_manual_protected: int = 0

    def summary(self) -> str:
        return (
            f"seen={self.seen} created={self.created} updated={self.updated} "
            f"skipped(unusable={self.skipped_unusable}, "
            f"unknown_company={self.skipped_unknown_company}, "
            f"manual_protected={self.skipped_manual_protected})"
        )


def _find_company(name: str):
    cleaned = clean_company_name(name)
    return (
        Company.objects.filter(Q(name__iexact=cleaned) | Q(name__icontains=cleaned))
        .order_by("name")
        .first()
    )


def _find_existing_opportunity(company: Company, listing: NormalizedListing):
    by_source = Opportunity.objects.filter(
        company=company, role__iexact=listing.role, source_url=listing.source_url
    ).first()
    if by_source:
        return by_source

    if listing.expected_hiring_window_start and listing.expected_hiring_window_end:
        return Opportunity.objects.filter(
            company=company,
            role__iexact=listing.role,
            expected_hiring_window_start__lte=listing.expected_hiring_window_end,
            expected_hiring_window_end__gte=listing.expected_hiring_window_start,
        ).first()

    return None


def import_listings(listings: List[NormalizedListing]) -> ImportStats:
    stats = ImportStats()

    for listing in listings:
        stats.seen += 1

        if not listing.is_usable():
            stats.skipped_unusable += 1
            logger.debug("Skipping unusable listing: %s / %s", listing.company_name, listing.role)
            continue

        company = _find_company(listing.company_name)
        if company is None:
            stats.skipped_unknown_company += 1
            logger.info(
                "Unknown company '%s' from source '%s' - add it via seed/admin to start importing its listings.",
                listing.company_name,
                listing.source_name,
            )
            continue

        existing = _find_existing_opportunity(company, listing)

        if existing and existing.source == SourceType.MANUAL:
            stats.skipped_manual_protected += 1
            continue

        defaults = {
            "opportunity_type": listing.opportunity_type,
            "expected_registration_start": listing.expected_registration_start,
            "expected_registration_end": listing.expected_registration_end,
            "expected_hiring_window_end": listing.expected_hiring_window_end
            or (existing.expected_hiring_window_end if existing else listing.expected_hiring_window_start),
            "career_portal_link": listing.career_portal_link or (existing.career_portal_link if existing else ""),
            "source": SourceType.SCRAPER,
            "source_url": listing.source_url,
            "is_date_confirmed": True,
            "notes": listing.notes or (existing.notes if existing else ""),
        }
        if existing is None:
            defaults["status"] = OpportunityStatus.UPCOMING

        opp, created = Opportunity.objects.update_or_create(
            company=company,
            role=listing.role,
            expected_hiring_window_start=listing.expected_hiring_window_start,
            defaults=defaults,
        )

        if created:
            stats.created += 1
        else:
            stats.updated += 1

    logger.info("Import complete: %s", stats.summary())
    return stats
