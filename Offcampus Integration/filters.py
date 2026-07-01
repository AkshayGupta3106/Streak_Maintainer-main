"""
hiring_tracker/api/filters.py

django-filter FilterSet for Opportunity. Using a proper FilterSet
instead of manual query-param checking means the API gets automatic
validation, consistent ?param=value syntax, and self-describing
filter metadata for the browsable API.

Install requirement: django-filter (add to requirements.txt if missing)
Also add 'django_filters' to INSTALLED_APPS and set:
    REST_FRAMEWORK = {
        'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend', ...]
    }
"""

from datetime import date, timedelta

import django_filters
from django.db.models import Q

from hiring_tracker.models import Opportunity, OpportunityStatus, OpportunityType


class OpportunityFilter(django_filters.FilterSet):
    opportunity_type = django_filters.MultipleChoiceFilter(choices=OpportunityType.choices)
    status = django_filters.MultipleChoiceFilter(choices=OpportunityStatus.choices)
    company = django_filters.CharFilter(field_name="company__name", lookup_expr="icontains")
    company_type = django_filters.CharFilter(field_name="company__company_type", lookup_expr="iexact")
    role = django_filters.CharFilter(lookup_expr="icontains")
    priority_level = django_filters.NumberFilter()
    priority_min = django_filters.NumberFilter(field_name="priority_level", lookup_expr="gte")
    is_date_confirmed = django_filters.BooleanFilter()
    window_start_after = django_filters.DateFilter(field_name="expected_hiring_window_start", lookup_expr="gte")
    window_start_before = django_filters.DateFilter(field_name="expected_hiring_window_start", lookup_expr="lte")

    # Urgency bucket: derives date range from the section name so the
    # frontend can ask ?urgency=apply_now rather than computing dates itself.
    urgency = django_filters.CharFilter(method="filter_urgency")

    class Meta:
        model = Opportunity
        fields = []

    def filter_urgency(self, queryset, name, value):
        today = date.today()
        bucket_ranges = {
            "apply_now":    (None, today + timedelta(days=14)),
            "coming_soon":  (today + timedelta(days=15), today + timedelta(days=30)),
            "prepare_now":  (today + timedelta(days=31), today + timedelta(days=60)),
            "long_term":    (today + timedelta(days=61), None),
            "missed":       (None, None),
        }
        if value == "missed":
            return queryset.filter(
                Q(status__in=["CLOSED", "MISSED"]) |
                Q(expected_hiring_window_end__lt=today)
            )
        if value not in bucket_ranges:
            return queryset
        start, end = bucket_ranges[value]
        qs = queryset.exclude(status__in=["CLOSED", "MISSED"])
        if start:
            qs = qs.filter(expected_hiring_window_start__gte=start)
        if end:
            qs = qs.filter(expected_hiring_window_start__lte=end)
        return qs
