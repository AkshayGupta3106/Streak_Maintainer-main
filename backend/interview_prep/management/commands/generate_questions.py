from django.core.management.base import BaseCommand, CommandError
from interview_prep.tasks import generate_daily_questions


class Command(BaseCommand):
    help = "Trigger daily interview questions generation manually."

    def handle(self, *args, **options):
        self.stdout.write("Starting daily question generation...")
        try:
            # We call the task function directly (not .delay()) to run synchronously
            generate_daily_questions()
            self.stdout.write(self.style.SUCCESS("Successfully generated daily questions!"))
        except Exception as e:
            raise CommandError(f"Generation failed: {e}")
