"""
python manage.py send_hiring_digest
python manage.py send_hiring_digest --to override@email.com
python manage.py send_hiring_digest --dry-run   # prints to console, no email sent

Cron (8 AM daily):
    0 8 * * * /path/to/venv/bin/python /path/to/manage.py send_hiring_digest >> /var/log/hiring_digest.log 2>&1

If you're already using Celery Beat, add to CELERY_BEAT_SCHEDULE instead:
    "hiring-digest": {
        "task": "hiring_tracker.tasks.send_digest_task",
        "schedule": crontab(hour=8, minute=0),
    }
"""

from django.core.management.base import BaseCommand, CommandError
from django.test.utils import override_settings

from hiring_tracker.email_service import send_daily_digest


class Command(BaseCommand):
    help = "Send the daily off-campus hiring digest email."

    def add_arguments(self, parser):
        parser.add_argument("--to", type=str, default="", help="Override recipient email.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print digest to stdout instead of sending email.",
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            # Swap email backend to console so output goes to stdout
            with override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"):
                sent = send_daily_digest(recipient=options["to"] or "preview@local")
        else:
            sent = send_daily_digest(recipient=options["to"])

        if sent:
            self.stdout.write(self.style.SUCCESS("Digest sent."))
        else:
            raise CommandError("Digest failed — check logs.")
