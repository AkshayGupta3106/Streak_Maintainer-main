# interview_prep — Daily AI/DS Interview Question Generator

Django app that generates 10 fresh AI Engineer / Data Science interview
questions daily, with structured model answers, using free-tier LLM APIs
(Gemini primary, Groq fallback) and DuckDuckGo search for freshness context.

## Setup

1. Copy this `interview_prep/` folder into your Django project root
   (next to `manage.py`).

2. Add to `INSTALLED_APPS` in `settings.py`:
   ```python
   INSTALLED_APPS = [
       ...
       "rest_framework",
       "interview_prep",
   ]
   ```

3. Add Celery Beat schedule to `settings.py`:
   ```python
   from celery.schedules import crontab

   CELERY_BEAT_SCHEDULE = {
       "generate-daily-interview-questions": {
           "task": "interview_prep.tasks.generate_daily_questions",
           "schedule": crontab(hour=6, minute=0),  # 6 AM daily
       },
   }
   ```

4. Wire URLs in your project's main `urls.py`:
   ```python
   path("api/", include("interview_prep.urls")),
   ```

5. Install dependencies:
   ```bash
   pip install ddgs google-generativeai groq djangorestframework celery
   ```

6. Add environment variables (`.env`, loaded via django-environ):
   ```
   GEMINI_API_KEY=your_key_here
   GROQ_API_KEY=your_key_here
   ```
   - Get Gemini key (no card required): https://ai.google.dev
   - Get Groq key (no card required): https://console.groq.com

7. Run migrations:
   ```bash
   python manage.py makemigrations interview_prep
   python manage.py migrate
   ```

## Manual test run (before trusting the daily cron)

```python
from interview_prep.tasks import generate_daily_questions
generate_daily_questions.delay()
```

Then check `GenerationRun` in Django admin to confirm status = "success"
and inspect `error_log` if anything failed.

## API endpoints

- `GET /api/questions/` — all questions (filterable by `?category=` and `?difficulty=`)
- `GET /api/questions/today/` — today's batch of 10
- `POST /api/questions/{id}/rate/` — body `{"rating": 1-5}`

## File structure

```
interview_prep/
├── __init__.py
├── apps.py
├── models.py          # GenerationRun, DailyInterviewQuestion
├── admin.py
├── serializers.py
├── views.py
├── urls.py
├── tasks.py            # Celery task: generate_daily_questions
├── migrations/
│   └── __init__.py
└── services/
    ├── __init__.py
    ├── search.py        # DuckDuckGo context gathering
    ├── llm_client.py     # Gemini + Groq generation with fallback
    └── dedup.py          # Embedding-based duplicate detection
```

## Notes

- Google's Gemini free tier quotas were tightened in late 2025 — verify
  current limits at ai.google.dev before scaling usage.
- `ddgs` (DuckDuckGo search) is unofficial and can be rate-limited under
  heavy load; swap in Serper.dev's free tier as a fallback if it becomes
  unreliable.
- SQLite doesn't support vector columns, so embeddings are stored as
  JSON and compared with plain Python cosine similarity — fine at this
  scale (tens of questions/day). Move to Postgres + pgvector if this
  grows significantly.
