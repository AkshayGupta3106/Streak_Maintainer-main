"""
hiring_tracker/api/urls.py

In your project's main urls.py, add:
    path("api/hiring/", include("hiring_tracker.api.urls")),
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AnalyticsView,
    CompanyViewSet,
    DashboardView,
    HiringSeasonViewSet,
    OpportunityViewSet,
    ScrapeView,
    TimelineView,
)

router = DefaultRouter()
router.register("opportunities", OpportunityViewSet, basename="opportunity")
router.register("companies", CompanyViewSet, basename="company")
router.register("seasons", HiringSeasonViewSet, basename="season")

urlpatterns = [
    path("", include(router.urls)),
    path("dashboard/", DashboardView.as_view(), name="hiring-dashboard"),
    path("analytics/", AnalyticsView.as_view(), name="hiring-analytics"),
    path("timeline/", TimelineView.as_view(), name="hiring-timeline"),
    path("scrape/", ScrapeView.as_view(), name="hiring-scrape"),
]

# Calendar endpoints (appended by section 4)
from hiring_tracker.calendar_service import CalendarICSView, CalendarEventsView

urlpatterns += [
    path("calendar.ics", CalendarICSView.as_view(), name="hiring-calendar-ics"),
    path("calendar/events/", CalendarEventsView.as_view(), name="hiring-calendar-events"),
]
