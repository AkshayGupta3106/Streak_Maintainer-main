from django.core.management.base import BaseCommand, CommandError
from interview_prep.tasks import generate_daily_questions


class Command(BaseCommand):
    help = "Trigger daily interview questions generation manually."

    def handle(self, *args, **options):
        self.stdout.write("Starting daily question generation...")
        try:
            # We call the task function directly (not .delay()) to run synchronously
            res = generate_daily_questions()
            if res == "skipped (already exists)":
                self.stdout.write(self.style.WARNING("Skipped: 10 or more daily questions already exist for today."))
            else:
                self.stdout.write(self.style.SUCCESS("Successfully generated daily questions!"))
        except Exception as e:
            raise CommandError(f"Generation failed: {e}")
