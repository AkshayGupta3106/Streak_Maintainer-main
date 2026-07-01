"""
hiring_tracker/models.py

Schema design notes:

- Company: one row per recruiter (TCS, Infosys, Microsoft, ...).
- HiringSeason: a *template* describing a company's recurring hiring
  pattern (e.g. "TCS NQT Cycle" typically runs Sept-Nov every year).
  The seeder uses these templates to generate concrete Opportunity
  rows each year. Scrapers (section 2) will also reference these
  templates to know which company/season a scraped listing belongs to.
- Opportunity: the actual trackable record shown on the dashboard.
  Urgency (which dashboard section / color it falls into) is computed
  on the fly from dates rather than stored, so it never goes stale.
"""

from django.db import models
from django.utils import timezone


class OpportunityType(models.TextChoices):
    INTERNSHIP = "INTERNSHIP", "Internship"
    FULL_TIME = "FULL_TIME", "Full-Time"
    HACKATHON = "HACKATHON", "Hackathon"
    OA = "OA", "Online Assessment"
    GRAD_PROGRAM = "GRAD_PROGRAM", "Graduate Program"


class OpportunityStatus(models.TextChoices):
    UPCOMING = "UPCOMING", "Upcoming"
    REGISTRATION_OPEN = "REGISTRATION_OPEN", "Registration Open"
    APPLY_NOW = "APPLY_NOW", "Apply Now"
    OA_EXPECTED = "OA_EXPECTED", "OA Expected"
    INTERVIEW_PHASE = "INTERVIEW_PHASE", "Interview Phase"
    CLOSED = "CLOSED", "Closed"
    MISSED = "MISSED", "Missed"


class PriorityLevel(models.IntegerChoices):
    LOW = 1, "Low"
    MEDIUM = 2, "Medium"
    HIGH = 3, "High"
    CRITICAL = 4, "Critical"


class SourceType(models.TextChoices):
    SEED = "SEED", "Pre-seeded calendar data"
    SCRAPER = "SCRAPER", "Automated scraper"
    MANUAL = "MANUAL", "Manually added"


class CompanyType(models.TextChoices):
    IT_SERVICES = "IT_SERVICES", "IT Services"
    PRODUCT = "PRODUCT", "Product"
    CORE = "CORE", "Core / Manufacturing"
    FINANCE = "FINANCE", "Finance / Consulting"
    STARTUP = "STARTUP", "Startup"
    OTHER = "OTHER", "Other"


class Company(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=160, unique=True)
    company_type = models.CharField(
        max_length=20, choices=CompanyType.choices, default=CompanyType.OTHER
    )
    career_portal_base_url = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class HiringSeason(models.Model):
    """Recurring hiring pattern template for a company."""

    class RecurrencePattern(models.TextChoices):
        ANNUAL = "ANNUAL", "Annual"
        BIANNUAL = "BIANNUAL", "Twice a year"
        IRREGULAR = "IRREGULAR", "Irregular"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="hiring_seasons"
    )
    name = models.CharField(max_length=200)
    opportunity_type = models.CharField(
        max_length=20, choices=OpportunityType.choices
    )
    recurrence_pattern = models.CharField(
        max_length=20,
        choices=RecurrencePattern.choices,
        default=RecurrencePattern.ANNUAL,
    )
    # Typical month range this season falls in, used to project next
    # year's expected dates when no scraped data is available yet.
    typical_window_start_month = models.PositiveSmallIntegerField()
    typical_window_end_month = models.PositiveSmallIntegerField()
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__name", "name"]

    def __str__(self):
        return f"{self.company.name} - {self.name}"


class Opportunity(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="opportunities"
    )
    hiring_season = models.ForeignKey(
        HiringSeason,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opportunities",
    )
    role = models.CharField(max_length=200)
    opportunity_type = models.CharField(
        max_length=20, choices=OpportunityType.choices
    )

    expected_registration_start = models.DateField(null=True, blank=True)
    expected_registration_end = models.DateField(null=True, blank=True)
    expected_hiring_window_start = models.DateField()
    expected_hiring_window_end = models.DateField()

    career_portal_link = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    priority_level = models.IntegerField(
        choices=PriorityLevel.choices, default=PriorityLevel.MEDIUM
    )
    status = models.CharField(
        max_length=20, choices=OpportunityStatus.choices, default=OpportunityStatus.UPCOMING
    )

    source = models.CharField(
        max_length=20, choices=SourceType.choices, default=SourceType.SEED
    )
    source_url = models.URLField(blank=True)
    is_date_confirmed = models.BooleanField(
        default=False,
        help_text="False if dates are projected from typical pattern, True if confirmed via official source/scraper.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["expected_hiring_window_start"]
        indexes = [
            models.Index(fields=["expected_hiring_window_start"]),
            models.Index(fields=["status"]),
            models.Index(fields=["opportunity_type"]),
        ]

    def __str__(self):
        return f"{self.company.name} - {self.role} ({self.expected_hiring_window_start})"

    # --- Urgency calculation -------------------------------------------------
    # Computed at read time so the dashboard never shows stale buckets.
    # Thresholds match the product spec: 14 / 30 / 60 day windows.

    def days_until_hiring(self) -> int:
        today = timezone.now().date()
        return (self.expected_hiring_window_start - today).days

    def is_currently_active(self) -> bool:
        today = timezone.now().date()
        return self.expected_hiring_window_start <= today <= self.expected_hiring_window_end

    def urgency_bucket(self) -> tuple[str, str]:
        """Returns (section_key, color_key)."""
        if self.status in (OpportunityStatus.CLOSED, OpportunityStatus.MISSED):
            return "missed", "grey"

        if self.is_currently_active():
            return "apply_now", "red"

        days = self.days_until_hiring()

        if days < 0:
            return "missed", "grey"
        if days <= 14:
            return "apply_now", "red"
        if days <= 30:
            return "coming_soon", "yellow"
        if days <= 60:
            return "prepare_now", "green"
        return "long_term", "blue"
