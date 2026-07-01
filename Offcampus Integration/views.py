"""
hiring_tracker/api/views.py

Endpoints:
  GET  /api/hiring/opportunities/              list, filtered
  GET  /api/hiring/opportunities/<id>/         detail
  POST /api/hiring/opportunities/              create (manual adds)
  PATCH/PUT /api/hiring/opportunities/<id>/    update
  DELETE    /api/hiring/opportunities/<id>/    delete

  GET  /api/hiring/companies/                  list
  GET  /api/hiring/seasons/                    list

  GET  /api/hiring/dashboard/                  all 5 urgency buckets in one shot
  GET  /api/hiring/analytics/                  counts + monthly distribution
  GET  /api/hiring/timeline/                   hiring-season roadmap data

  POST /api/hiring/scrape/                     trigger scraper run (async-optional)
"""

import logging
from collections import defaultdict
from datetime import date, timedelta

from django.db.models import Count, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from hiring_tracker.models import Company, HiringSeason, Opportunity, OpportunityStatus
from hiring_tracker.scrapers.registry import get_all_scrapers
from hiring_tracker.scrapers.importer import import_listings

from .filters import OpportunityFilter
from .serializers import (
    CompanySerializer,
    HiringSeasonSerializer,
    OpportunitySerializer,
    OpportunityWriteSerializer,
)

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

logger = logging.getLogger("hiring_tracker.api")


class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Company.objects.filter(is_active=True)
    serializer_class = CompanySerializer
    filter_backends = [SearchFilter]
    search_fields = ["name"]


class HiringSeasonViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HiringSeason.objects.select_related("company").filter(is_active=True)
    serializer_class = HiringSeasonSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["company", "opportunity_type"]


class OpportunityViewSet(viewsets.ModelViewSet):
    queryset = (
        Opportunity.objects
        .select_related("company", "hiring_season")
        .order_by("expected_hiring_window_start")
    )
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = OpportunityFilter
    search_fields = ["company__name", "role", "notes"]
    ordering_fields = ["expected_hiring_window_start", "priority_level", "company__name"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return OpportunityWriteSerializer
        return OpportunitySerializer

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        """PATCH /api/hiring/opportunities/<id>/status/  {status: "APPLY_NOW"}"""
        opp = self.get_object()
        new_status = request.data.get("status")
        if new_status not in OpportunityStatus.values:
            return Response(
                {"error": f"Invalid status. Choices: {OpportunityStatus.values}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        opp.status = new_status
        opp.save(update_fields=["status", "updated_at"])
        return Response(OpportunitySerializer(opp).data)


class DashboardView(APIView):
    """
    GET /api/hiring/dashboard/

    Returns all 5 urgency buckets in one request so the React dashboard
    never needs to fire 5 separate API calls on mount.

    Response shape:
    {
      "apply_now":   [...],
      "coming_soon": [...],
      "prepare_now": [...],
      "long_term":   [...],
      "missed":      [...]
    }
    """

    def get(self, request):
        today = date.today()
        base_qs = (
            Opportunity.objects
            .select_related("company", "hiring_season")
            .order_by("expected_hiring_window_start")
        )

        active_or_imminent = base_qs.filter(
            expected_hiring_window_start__lte=today + timedelta(days=14),
            expected_hiring_window_end__gte=today,
        ).exclude(status__in=["CLOSED", "MISSED"])

        coming_soon = base_qs.filter(
            expected_hiring_window_start__gt=today + timedelta(days=14),
            expected_hiring_window_start__lte=today + timedelta(days=30),
        ).exclude(status__in=["CLOSED", "MISSED"])

        prepare_now = base_qs.filter(
            expected_hiring_window_start__gt=today + timedelta(days=30),
            expected_hiring_window_start__lte=today + timedelta(days=60),
        ).exclude(status__in=["CLOSED", "MISSED"])

        long_term = base_qs.filter(
            expected_hiring_window_start__gt=today + timedelta(days=60),
        ).exclude(status__in=["CLOSED", "MISSED"])

        missed = base_qs.filter(
            Q(status__in=["CLOSED", "MISSED"]) |
            Q(expected_hiring_window_end__lt=today)
        )

        s = OpportunitySerializer
        return Response({
            "apply_now":   s(active_or_imminent, many=True).data,
            "coming_soon": s(coming_soon, many=True).data,
            "prepare_now": s(prepare_now, many=True).data,
            "long_term":   s(long_term, many=True).data,
            "missed":      s(missed, many=True).data,
            "meta": {
                "today": today,
                "counts": {
                    "apply_now":   active_or_imminent.count(),
                    "coming_soon": coming_soon.count(),
                    "prepare_now": prepare_now.count(),
                    "long_term":   long_term.count(),
                    "missed":      missed.count(),
                },
            },
        })


class AnalyticsView(APIView):
    """
    GET /api/hiring/analytics/

    {
      "totals": { upcoming, this_month, active, total },
      "by_type": { INTERNSHIP: N, FULL_TIME: N, ... },
      "by_company_type": { PRODUCT: N, IT_SERVICES: N, ... },
      "by_month": [ { month: "2026-09", count: 4 }, ... ]  // next 6 months
    }
    """

    def get(self, request):
        today = date.today()
        month_start = today.replace(day=1)
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        six_months_out = today + timedelta(days=180)

        active = Opportunity.objects.filter(
            expected_hiring_window_start__lte=today,
            expected_hiring_window_end__gte=today,
        ).exclude(status__in=["CLOSED", "MISSED"])

        upcoming = Opportunity.objects.filter(
            expected_hiring_window_start__gt=today
        ).exclude(status__in=["CLOSED", "MISSED"])

        this_month = Opportunity.objects.filter(
            expected_hiring_window_start__gte=month_start,
            expected_hiring_window_start__lt=next_month,
        ).exclude(status__in=["CLOSED", "MISSED"])

        by_type = (
            Opportunity.objects
            .exclude(status__in=["CLOSED", "MISSED"])
            .values("opportunity_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        by_company_type = (
            Opportunity.objects
            .exclude(status__in=["CLOSED", "MISSED"])
            .values("company__company_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Monthly distribution: bucket upcoming opps by hiring window start month
        monthly = defaultdict(int)
        for opp in Opportunity.objects.filter(
            expected_hiring_window_start__gte=today,
            expected_hiring_window_start__lte=six_months_out,
        ).exclude(status__in=["CLOSED", "MISSED"]).values("expected_hiring_window_start"):
            key = opp["expected_hiring_window_start"].strftime("%Y-%m")
            monthly[key] += 1

        by_month = [{"month": k, "count": v} for k, v in sorted(monthly.items())]

        return Response({
            "totals": {
                "upcoming": upcoming.count(),
                "this_month": this_month.count(),
                "active": active.count(),
                "total": Opportunity.objects.count(),
            },
            "by_type": {row["opportunity_type"]: row["count"] for row in by_type},
            "by_company_type": {row["company__company_type"]: row["count"] for row in by_company_type},
            "by_month": by_month,
        })


class TimelineView(APIView):
    """
    GET /api/hiring/timeline/

    Returns the 4-season roadmap for the Hiring Season Timeline widget.
    Each season includes the opportunities that fall within it.
    """

    SEASONS = [
        {"key": "jan_mar", "label": "January – March", "activity": "Peak Hiring Season", "months": [1, 2, 3]},
        {"key": "apr_jun", "label": "April – June", "activity": "Strong Hiring Activity", "months": [4, 5, 6]},
        {"key": "jul_aug", "label": "July – August", "activity": "Moderate Activity", "months": [7, 8]},
        {"key": "sep_nov", "label": "September – November", "activity": "Peak Hiring Season", "months": [9, 10, 11]},
        {"key": "dec",     "label": "December", "activity": "Slow Hiring Season", "months": [12]},
    ]

    def get(self, request):
        all_opps = (
            Opportunity.objects
            .select_related("company", "hiring_season")
            .exclude(status__in=["CLOSED", "MISSED"])
            .values(
                "id", "role",
                "company__name",
                "expected_hiring_window_start",
                "expected_hiring_window_end",
                "opportunity_type",
                "career_portal_link",
            )
        )

        opp_by_month = defaultdict(list)
        for opp in all_opps:
            m = opp["expected_hiring_window_start"].month
            opp_by_month[m].append(opp)

        result = []
        for season in self.SEASONS:
            opps = []
            for m in season["months"]:
                opps.extend(opp_by_month[m])
            result.append({
                **season,
                "opportunities": opps,
                "opportunity_count": len(opps),
            })

        return Response(result)


class ScrapeView(APIView):
    """
    POST /api/hiring/scrape/
    Body: { "sources": ["internshala", "unstop"] }  OR  {} to run all

    Runs scrapers synchronously. For production you'd kick off a Celery
    task here instead and return a task ID - see the comment in the body.
    """

    def post(self, request):
        requested = request.data.get("sources", [])
        all_scrapers = get_all_scrapers()

        if requested:
            scrapers = [s for s in all_scrapers if s.source_name in requested]
            unknown = set(requested) - {s.source_name for s in scrapers}
            if unknown:
                return Response(
                    {"error": f"Unknown sources: {unknown}. Available: {[s.source_name for s in all_scrapers]}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            scrapers = all_scrapers

        # --- For production: swap the block below for a Celery task dispatch ---
        # from hiring_tracker.tasks import run_scrapers_task
        # task = run_scrapers_task.delay([s.source_name for s in scrapers])
        # return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)
        # -----------------------------------------------------------------------

        results = {}
        for scraper in scrapers:
            try:
                listings = scraper.run()
                stats = import_listings(listings)
                results[scraper.source_name] = {
                    "status": "ok",
                    "seen": stats.seen,
                    "created": stats.created,
                    "updated": stats.updated,
                }
            except Exception as exc:
                logger.exception("Scraper failed: %s", scraper.source_name)
                results[scraper.source_name] = {"status": "error", "error": str(exc)}

        return Response({"results": results})
