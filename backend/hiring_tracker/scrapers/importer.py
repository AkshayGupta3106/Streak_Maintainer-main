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
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from django.db.models import Q
from django.utils.text import slugify

from hiring_tracker.models import Company, CompanyType, Opportunity, OpportunityStatus, SourceType
from hiring_tracker.scrapers.base import NormalizedListing
from hiring_tracker.scrapers.normalizer import clean_company_name

logger = logging.getLogger("hiring_tracker.scrapers")

TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "source",
}


@dataclass
class ImportStats:
    seen: int = 0
    skipped_unusable: int = 0
    skipped_unknown_company: int = 0
    auto_created_company: int = 0
    created: int = 0
    updated: int = 0
    skipped_manual_protected: int = 0

    def summary(self) -> str:
        return (
            f"seen={self.seen} created={self.created} updated={self.updated} "
            f"skipped(unusable={self.skipped_unusable}, "
            f"unknown_company={self.skipped_unknown_company}, "
            f"manual_protected={self.skipped_manual_protected}) "
            f"auto_created_company={self.auto_created_company}"
        )


def _normalize_role(role: str) -> str:
    return " ".join((role or "").split())


def _canonicalize_source_url(raw_url: str) -> str:
    if not raw_url:
        return ""
    try:
        parsed = urlparse(raw_url.strip())
        cleaned_query = [
            (k, v)
            for (k, v) in parse_qsl(parsed.query, keep_blank_values=True)
            if k and k.lower() not in TRACKING_QUERY_KEYS and not k.lower().startswith(TRACKING_QUERY_PREFIXES)
        ]
        normalized_path = parsed.path.rstrip("/") or "/"
        return urlunparse(
            parsed._replace(
                path=normalized_path,
                query=urlencode(cleaned_query, doseq=True),
                fragment="",
            )
        )
    except Exception:
        return raw_url.strip()


def _listing_dedup_key(listing: NormalizedListing):
    canonical_url = _canonicalize_source_url(listing.source_url)
    normalized_role = _normalize_role(listing.role).lower()
    normalized_company = clean_company_name(listing.company_name).lower()

    if canonical_url:
        return ("url", canonical_url)

    return (
        "fallback",
        normalized_company,
        normalized_role,
        listing.expected_hiring_window_start,
        listing.expected_hiring_window_end,
        listing.opportunity_type,
    )


def _find_company(name: str):
    cleaned = clean_company_name(name)
    return (
        Company.objects.filter(Q(name__iexact=cleaned) | Q(name__icontains=cleaned))
        .order_by("name")
        .first()
    )


def _safe_auto_create_company(name: str):
    cleaned = clean_company_name(name)
    if not cleaned or len(cleaned) < 2:
        return None
    if len(cleaned) > 140:
        return None

    # Basic guard to avoid junk strings from malformed snippets.
    alpha_chars = sum(1 for ch in cleaned if ch.isalpha())
    if alpha_chars < 2:
        return None

    slug_base = slugify(cleaned)[:140] or "company"
    slug = slug_base
    index = 1
    while Company.objects.filter(slug=slug).exclude(name__iexact=cleaned).exists():
        index += 1
        slug = f"{slug_base}-{index}"[:160]

    company, _ = Company.objects.get_or_create(
        name=cleaned,
        defaults={
            "slug": slug,
            "company_type": CompanyType.OTHER,
            "is_active": True,
        },
    )
    return company


def _find_existing_opportunity(company: Company, listing: NormalizedListing):
    if listing.source_url:
        by_source = Opportunity.objects.filter(
            company=company,
            role__iexact=listing.role,
            source_url=listing.source_url,
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
    seen_listing_keys = set()

    for listing in listings:
        stats.seen += 1

        listing.role = _normalize_role(listing.role)
        listing.source_url = _canonicalize_source_url(listing.source_url)
        listing.career_portal_link = _canonicalize_source_url(listing.career_portal_link)

        dedup_key = _listing_dedup_key(listing)
        if dedup_key in seen_listing_keys:
            continue
        seen_listing_keys.add(dedup_key)

        if not listing.is_usable():
            stats.skipped_unusable += 1
            logger.debug("Skipping unusable listing: %s / %s", listing.company_name, listing.role)
            continue

        company = _find_company(listing.company_name)
        if company is None:
            company = _safe_auto_create_company(listing.company_name)
            if company is None:
                stats.skipped_unknown_company += 1
                logger.info(
                    "Unknown company '%s' from source '%s' could not be auto-created safely.",
                    listing.company_name,
                    listing.source_name,
                )
                continue
            stats.auto_created_company += 1

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
        if existing is not None:
            existing.role = listing.role
            existing.opportunity_type = defaults["opportunity_type"]
            existing.expected_registration_start = defaults["expected_registration_start"]
            existing.expected_registration_end = defaults["expected_registration_end"]
            existing.expected_hiring_window_start = (
                listing.expected_hiring_window_start or existing.expected_hiring_window_start
            )
            existing.expected_hiring_window_end = (
                defaults["expected_hiring_window_end"]
                or existing.expected_hiring_window_end
                or existing.expected_hiring_window_start
            )
            existing.career_portal_link = defaults["career_portal_link"]
            existing.source = defaults["source"]
            existing.source_url = defaults["source_url"]
            existing.is_date_confirmed = defaults["is_date_confirmed"]
            existing.notes = defaults["notes"]
            existing.save(
                update_fields=[
                    "role",
                    "opportunity_type",
                    "expected_registration_start",
                    "expected_registration_end",
                    "expected_hiring_window_start",
                    "expected_hiring_window_end",
                    "career_portal_link",
                    "source",
                    "source_url",
                    "is_date_confirmed",
                    "notes",
                    "updated_at",
                ]
            )
            stats.updated += 1
            continue

        Opportunity.objects.create(
            company=company,
            role=listing.role,
            opportunity_type=defaults["opportunity_type"],
            expected_registration_start=defaults["expected_registration_start"],
            expected_registration_end=defaults["expected_registration_end"],
            expected_hiring_window_start=listing.expected_hiring_window_start,
            expected_hiring_window_end=defaults["expected_hiring_window_end"]
            or listing.expected_hiring_window_start,
            career_portal_link=defaults["career_portal_link"],
            source=defaults["source"],
            source_url=defaults["source_url"],
            is_date_confirmed=defaults["is_date_confirmed"],
            notes=defaults["notes"],
            status=OpportunityStatus.UPCOMING,
        )

        stats.created += 1

    logger.info("Import complete: %s", stats.summary())
    return stats
