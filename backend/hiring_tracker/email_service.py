"""
hiring_tracker/email_service.py

Decoupled from the management command so the same function can be called
from a Celery beat task, a test, or the management command without
duplicating logic.

Required Django settings (in addition to standard EMAIL_* settings):

    HIRING_TRACKER = {
        "DIGEST_RECIPIENT": "you@gmail.com",     # who gets the email
        "DIGEST_FROM": "hiring-tracker@yourdomain.com",
    }

For local dev with Gmail:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.gmail.com"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = "you@gmail.com"
    EMAIL_HOST_PASSWORD = "<app-password>"         # not your login password

For local testing without sending:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
"""

import logging
from datetime import date, timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.db.models import Q

from hiring_tracker.models import Opportunity, OpportunityStatus

logger = logging.getLogger("hiring_tracker.email")


def _get_config() -> dict:
    cfg = getattr(settings, "HIRING_TRACKER", {})
    return {
        "recipient": cfg.get("DIGEST_RECIPIENT", ""),
        "from_email": cfg.get("DIGEST_FROM", settings.DEFAULT_FROM_EMAIL),
    }


def _fetch_upcoming(days_from: int, days_to: int, today: date):
    return list(
        Opportunity.objects
        .select_related("company")
        .filter(
            expected_hiring_window_start__gte=today + timedelta(days=days_from),
            expected_hiring_window_start__lte=today + timedelta(days=days_to),
        )
        .exclude(status__in=[OpportunityStatus.CLOSED, OpportunityStatus.MISSED])
        .order_by("expected_hiring_window_start")
    )


def send_daily_digest(recipient: str = "") -> bool:
    """
    Build and send the daily hiring digest.
    Returns True if the email was sent, False if skipped/failed.
    recipient overrides HIRING_TRACKER.DIGEST_RECIPIENT when provided.
    """
    config = _get_config()
    to = recipient or config["recipient"]

    if not to:
        logger.error(
            "No recipient configured. Set HIRING_TRACKER['DIGEST_RECIPIENT'] in settings."
        )
        return False

    today = date.today()

    opening_7  = _fetch_upcoming(0,  7,  today)
    opening_14 = _fetch_upcoming(8,  14, today)
    opening_30 = _fetch_upcoming(15, 30, today)

    context = {
        "today": today,
        "opening_7":  opening_7,
        "opening_14": opening_14,
        "opening_30": opening_30,
    }

    subject = f"[Hiring Tracker] Upcoming Off-Campus Opportunities — {today.strftime('%d %b %Y')}"
    text_body = render_to_string("hiring_tracker/email/digest.txt", context)
    html_body = render_to_string("hiring_tracker/email/digest.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=config["from_email"],
        to=[to],
    )
    msg.attach_alternative(html_body, "text/html")

    try:
        msg.send()
        logger.info(
            "Digest sent to %s: 7d=%d 14d=%d 30d=%d",
            to, len(opening_7), len(opening_14), len(opening_30),
        )
        return True
    except Exception:
        logger.exception("Failed to send digest email to %s", to)
        return False
