import logging
from celery import shared_task
from django.utils import timezone

from .models import DailyInterviewQuestion, GenerationRun
from .services.search import gather_daily_context
from .services.llm_client import generate_questions
from .services.dedup import embed_text, is_duplicate

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def generate_daily_questions(self):
    run = GenerationRun.objects.create(status="pending")

    try:
        queries, context_text = gather_daily_context(n_queries=4)
        run.search_queries_used = queries
        run.save(update_fields=["search_queries_used"])

        questions_raw, provider = generate_questions(context_text)
        run.llm_provider_used = provider

        saved_count = 0
        rejected_count = 0

        for q in questions_raw:
            try:
                embedding = embed_text(q["question"])

                if is_duplicate(embedding):
                    rejected_count += 1
                    continue

                DailyInterviewQuestion.objects.create(
                    run=run,
                    question=q["question"],
                    category=q["category"],
                    difficulty=q["difficulty"],
                    company_style=q.get("company_style", ""),
                    model_answer=q["model_answer"],
                    follow_up_questions=q.get("follow_up_questions", []),
                    source_context=context_text[:2000],
                    embedding=embedding,
                )
                saved_count += 1

            except Exception as e:
                logger.error(f"Failed to save question: {e}")
                continue

        run.questions_generated = saved_count
        run.questions_rejected_duplicate = rejected_count
        run.status = "success" if saved_count >= 8 else "partial"
        run.save()

        logger.info(f"Daily generation complete: {saved_count} saved, {rejected_count} rejected as dupes")

    except Exception as e:
        run.status = "failed"
        run.error_log = str(e)
        run.save()
        logger.error(f"Daily question generation failed: {e}")
        raise self.retry(exc=e, countdown=300)
