"""
hiring_tracker/calendar_service.py

Two things:

1. build_ical()    — generates a valid RFC 5545 .ics file from all
                     non-closed Opportunities. Subscribe to it in any
                     calendar app via a URL like /api/hiring/calendar.ics

2. CalendarEventsView — returns month-bucketed events as JSON for the
                        React calendar component so it doesn't have to
                        parse iCal.

No Google API credentials needed for either. If you want two-way Google
Calendar sync later, the iCal URL is the easiest path: add it as a
subscribed calendar in Google Calendar and it auto-syncs every few hours.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List

from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone as django_tz
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions

from hiring_tracker.models import Opportunity, OpportunityStatus

_ICAL_DT = "%Y%m%dT%H%M%SZ"
_ICAL_DATE = "%Y%m%d"


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    """RFC 5545 line folding: max 75 octets per line, continuation with CRLF + space."""
    result = []
    while len(line.encode("utf-8")) > 75:
        # Cut at 75 bytes, not chars
        chunk = line.encode("utf-8")[:75].decode("utf-8", errors="ignore")
        result.append(chunk)
        line = " " + line[len(chunk):]
    result.append(line)
    return "\r\n".join(result)


def _opp_to_vevent(opp: Opportunity, now_utc: str) -> List[str]:
    start = opp.expected_hiring_window_start.strftime(_ICAL_DATE)
    # DTEND is exclusive in iCal all-day events
    end = (opp.expected_hiring_window_end + timedelta(days=1)).strftime(_ICAL_DATE)
    summary = f"{opp.company.name} — {opp.role}"
    desc_parts = [
        f"Type: {opp.get_opportunity_type_display()}",
        f"Status: {opp.get_status_display()}",
        f"Priority: {opp.get_priority_level_display()}",
    ]
    if opp.career_portal_link:
        desc_parts.append(f"Portal: {opp.career_portal_link}")
    if opp.notes:
        desc_parts.append(opp.notes[:300])
    if not opp.is_date_confirmed:
        desc_parts.append("⚠ Dates projected — confirm on official portal.")

    # Color category by urgency
    color_map = {"red": "RED", "yellow": "YELLOW", "green": "GREEN", "blue": "BLUE", "grey": "GRAY"}
    _, color_key = opp.urgency_bucket()
    color = color_map.get(color_key, "BLUE")

    uid = f"hiringtracker-{opp.pk}@offcampus"

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now_utc}",
        f"DTSTART;VALUE=DATE:{start}",
        f"DTEND;VALUE=DATE:{end}",
        _fold(f"SUMMARY:{_escape(summary)}"),
        _fold(f"DESCRIPTION:{_escape(chr(10).join(desc_parts))}"),
        f"COLOR:{color}",
        f"CATEGORIES:{opp.get_opportunity_type_display()}",
    ]
    if opp.career_portal_link:
        lines.append(f"URL:{opp.career_portal_link}")
    lines.append("END:VEVENT")
    return lines


def build_ical() -> str:
    """Return a full .ics string for all non-closed opportunities."""
    now_utc = datetime.now(timezone.utc).strftime(_ICAL_DT)
    opps = (
        Opportunity.objects
        .select_related("company", "hiring_season")
        .exclude(status__in=[OpportunityStatus.CLOSED, OpportunityStatus.MISSED])
        .order_by("expected_hiring_window_start")
    )

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Off-Campus Hiring Tracker 2026//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Off-Campus Hiring 2026",
        "X-WR-CALDESC:Hiring windows and registration deadlines for off-campus drives",
        "X-WR-TIMEZONE:Asia/Kolkata",
        "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
    ]

    for opp in opps:
        lines.extend(_opp_to_vevent(opp, now_utc))

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


# ---------------------------------------------------------------------------
# API views
# ---------------------------------------------------------------------------

class CalendarICSView(APIView):
    permission_classes = [permissions.AllowAny]
    """
    GET /api/hiring/calendar.ics

    Returns a downloadable .ics file. Subscribe to this URL in Google
    Calendar → "From URL" to get automatic sync every 6 hours.
    """

    def get(self, request):
        ics_content = build_ical()
        response = HttpResponse(ics_content, content_type="text/calendar; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="hiring_calendar.ics"'
        # Don't cache — each request should reflect latest DB state
        response["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response


class CalendarEventsView(APIView):
    """
    GET /api/hiring/calendar/events/?year=2026&month=9

    Returns all events that overlap the requested month, shaped for a
    React calendar component. Each event has start/end dates, color,
    and enough metadata to render a detail popover without a second request.

    Also returns prev_month/next_month metadata so the frontend can
    pre-fetch adjacent months without doing date math itself.
    """

    def get(self, request):
        today = date.today()
        year  = int(request.query_params.get("year",  today.year))
        month = int(request.query_params.get("month", today.month))

        month_start = date(year, month, 1)
        # Last day of month
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        opps = (
            Opportunity.objects
            .select_related("company")
            .filter(
                expected_hiring_window_start__lte=month_end,
                expected_hiring_window_end__gte=month_start,
            )
            .order_by("expected_hiring_window_start")
        )

        events = []
        for opp in opps:
            _, color = opp.urgency_bucket()
            events.append({
                "id":         opp.pk,
                "title":      f"{opp.company.name} — {opp.role}",
                "company":    opp.company.name,
                "role":       opp.role,
                "type":       opp.opportunity_type,
                "type_label": opp.get_opportunity_type_display(),
                "start":      opp.expected_hiring_window_start.isoformat(),
                "end":        opp.expected_hiring_window_end.isoformat(),
                "reg_start":  opp.expected_registration_start.isoformat() if opp.expected_registration_start else None,
                "reg_end":    opp.expected_registration_end.isoformat()   if opp.expected_registration_end   else None,
                "status":     opp.status,
                "color":      color,
                "portal":     opp.career_portal_link,
                "confirmed":  opp.is_date_confirmed,
                "days_until": opp.days_until_hiring(),
            })

        # Navigation helpers
        prev_month_date = month_start - timedelta(days=1)
        next_month_date = month_end   + timedelta(days=1)

        return Response({
            "year":  year,
            "month": month,
            "month_label": month_start.strftime("%B %Y"),
            "today": today.isoformat(),
            "events": events,
            "event_count": len(events),
            "nav": {
                "prev": {"year": prev_month_date.year, "month": prev_month_date.month},
                "next": {"year": next_month_date.year, "month": next_month_date.month},
            },
        })
