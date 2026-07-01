"""
Usage: python manage.py seed_hiring_calendar

Seeds the 10 recurring hirers named in the product spec with one
HiringSeason template each, then generates concrete Opportunity rows
for the current hiring cycle. Dates are approximate projections based
on each company's typical historical pattern (is_date_confirmed=False)
until a scraper (section 2) overwrites them with confirmed dates from
the official portal.

Safe to re-run: uses get_or_create / update_or_create throughout.
"""

from datetime import date

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from hiring_tracker.models import (
    Company,
    CompanyType,
    HiringSeason,
    Opportunity,
    OpportunityType,
    OpportunityStatus,
    PriorityLevel,
    SourceType,
)

# (name, company_type, career_portal_base_url)
COMPANIES = [
    ("TCS", CompanyType.IT_SERVICES, "https://www.tcs.com/careers"),
    ("Infosys", CompanyType.IT_SERVICES, "https://www.infosys.com/careers.html"),
    ("Accenture", CompanyType.IT_SERVICES, "https://www.accenture.com/in-en/careers"),
    ("Cognizant", CompanyType.IT_SERVICES, "https://careers.cognizant.com/"),
    ("Capgemini", CompanyType.IT_SERVICES, "https://www.capgemini.com/careers/"),
    ("Deloitte", CompanyType.FINANCE, "https://www2.deloitte.com/in/en/careers.html"),
    ("Microsoft", CompanyType.PRODUCT, "https://careers.microsoft.com/"),
    ("Google", CompanyType.PRODUCT, "https://careers.google.com/students/"),
    ("Amazon", CompanyType.PRODUCT, "https://www.amazon.jobs/en/teams/internships-for-students"),
    ("Goldman Sachs", CompanyType.FINANCE, "https://www.goldmansachs.com/careers/"),
]

# (company_name, season_name, opportunity_type, recurrence, typical_start_month, typical_end_month)
SEASON_TEMPLATES = [
    ("TCS", "TCS NQT Cycle", OpportunityType.FULL_TIME, "BIANNUAL", 8, 11),
    ("Infosys", "Infosys Hiring Season", OpportunityType.FULL_TIME, "ANNUAL", 8, 11),
    ("Accenture", "Accenture Hiring Season", OpportunityType.FULL_TIME, "ANNUAL", 9, 11),
    ("Cognizant", "Cognizant GenC Hiring", OpportunityType.FULL_TIME, "ANNUAL", 9, 11),
    ("Capgemini", "Capgemini Hiring Season", OpportunityType.FULL_TIME, "ANNUAL", 9, 11),
    ("Deloitte", "Deloitte Graduate Program", OpportunityType.GRAD_PROGRAM, "ANNUAL", 9, 11),
    ("Microsoft", "Microsoft Internship Season", OpportunityType.INTERNSHIP, "ANNUAL", 7, 9),
    ("Google", "Google STEP Season", OpportunityType.INTERNSHIP, "ANNUAL", 8, 10),
    ("Amazon", "Amazon Internship Season", OpportunityType.INTERNSHIP, "ANNUAL", 7, 9),
    ("Goldman Sachs", "Goldman Sachs Analyst/Intern Program", OpportunityType.GRAD_PROGRAM, "ANNUAL", 8, 9),
]

# Concrete 2026-cycle rows: (company_name, role, reg_start, reg_end, window_start, window_end, priority)
OPPORTUNITIES_2026 = [
    ("TCS", "NQT - Ninja/Digital", date(2026, 8, 1), date(2026, 8, 20), date(2026, 9, 1), date(2026, 11, 15), PriorityLevel.HIGH),
    ("Infosys", "Systems Engineer / SE Specialist", date(2026, 8, 5), date(2026, 8, 25), date(2026, 9, 5), date(2026, 11, 20), PriorityLevel.HIGH),
    ("Accenture", "Associate Software Engineer", date(2026, 9, 1), date(2026, 9, 20), date(2026, 9, 25), date(2026, 11, 25), PriorityLevel.MEDIUM),
    ("Cognizant", "GenC / GenC Elevate", date(2026, 9, 1), date(2026, 9, 20), date(2026, 9, 25), date(2026, 11, 25), PriorityLevel.MEDIUM),
    ("Capgemini", "Analyst Trainee", date(2026, 9, 5), date(2026, 9, 25), date(2026, 10, 1), date(2026, 11, 30), PriorityLevel.MEDIUM),
    ("Deloitte", "Analyst - Graduate Program", date(2026, 9, 5), date(2026, 9, 25), date(2026, 10, 1), date(2026, 11, 30), PriorityLevel.MEDIUM),
    ("Microsoft", "Software Engineer Intern", date(2026, 7, 10), date(2026, 8, 5), date(2026, 8, 10), date(2026, 9, 30), PriorityLevel.CRITICAL),
    ("Google", "STEP Intern", date(2026, 8, 1), date(2026, 8, 25), date(2026, 9, 1), date(2026, 10, 31), PriorityLevel.CRITICAL),
    ("Amazon", "SDE Intern", date(2026, 7, 5), date(2026, 7, 30), date(2026, 8, 5), date(2026, 9, 25), PriorityLevel.CRITICAL),
    ("Goldman Sachs", "Summer Analyst / New Analyst Program", date(2026, 8, 1), date(2026, 8, 20), date(2026, 8, 25), date(2026, 9, 30), PriorityLevel.HIGH),
]


class Command(BaseCommand):
    help = "Seed companies, recurring hiring season templates, and the current opportunity cycle."

    def handle(self, *args, **options):
        company_map = {}
        for name, ctype, portal in COMPANIES:
            company, created = Company.objects.update_or_create(
                name=name,
                defaults={
                    "slug": slugify(name),
                    "company_type": ctype,
                    "career_portal_base_url": portal,
                    "is_active": True,
                },
            )
            company_map[name] = company
            self.stdout.write(f"{'Created' if created else 'Updated'} company: {name}")

        season_map = {}
        for company_name, season_name, otype, recurrence, start_m, end_m in SEASON_TEMPLATES:
            season, created = HiringSeason.objects.update_or_create(
                company=company_map[company_name],
                name=season_name,
                defaults={
                    "opportunity_type": otype,
                    "recurrence_pattern": recurrence,
                    "typical_window_start_month": start_m,
                    "typical_window_end_month": end_m,
                },
            )
            season_map[company_name] = season
            self.stdout.write(f"{'Created' if created else 'Updated'} season: {season_name}")

        for company_name, role, reg_start, reg_end, win_start, win_end, priority in OPPORTUNITIES_2026:
            company = company_map[company_name]
            season = season_map[company_name]
            opp, created = Opportunity.objects.update_or_create(
                company=company,
                role=role,
                expected_hiring_window_start=win_start,
                defaults={
                    "hiring_season": season,
                    "opportunity_type": season.opportunity_type,
                    "expected_registration_start": reg_start,
                    "expected_registration_end": reg_end,
                    "expected_hiring_window_end": win_end,
                    "career_portal_link": company.career_portal_base_url,
                    "priority_level": priority,
                    "status": OpportunityStatus.UPCOMING,
                    "source": SourceType.SEED,
                    "is_date_confirmed": False,
                    "notes": "Projected from typical hiring pattern. Confirm exact dates on the official career portal before relying on them.",
                },
            )
            self.stdout.write(f"{'Created' if created else 'Updated'} opportunity: {company_name} - {role}")

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {len(COMPANIES)} companies, {len(SEASON_TEMPLATES)} season templates, "
            f"{len(OPPORTUNITIES_2026)} opportunities."
        ))
