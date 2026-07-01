import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class GenerationRun(models.Model):
    """Tracks each daily generation batch — useful for debugging/audit."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("partial", "Partial (some questions failed)"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run_date = models.DateField(auto_now_add=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    llm_provider_used = models.CharField(max_length=50, blank=True)  # "gemini" | "groq"
    search_queries_used = models.JSONField(default=list, blank=True)
    questions_generated = models.PositiveSmallIntegerField(default=0)
    questions_rejected_duplicate = models.PositiveSmallIntegerField(default=0)
    error_log = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-run_date"]

    def __str__(self):
        return f"Run {self.run_date} — {self.status}"


class DailyInterviewQuestion(models.Model):
    CATEGORY_CHOICES = [
        ("ml_fundamentals", "ML Fundamentals"),
        ("stats", "Statistics / Probability"),
        ("system_design", "ML/GenAI System Design"),
        ("coding", "Coding / Algorithms"),
        ("behavioral", "Behavioral / Case Study"),
        ("genai", "GenAI / LLM Specific"),
    ]

    DIFFICULTY_CHOICES = [
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(
        GenerationRun, on_delete=models.CASCADE, related_name="questions", null=True
    )

    question = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, db_index=True)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, db_index=True)
    company_style = models.CharField(max_length=100, blank=True)  # "Meta", "startup GenAI"

    model_answer = models.TextField()
    follow_up_questions = models.JSONField(default=list, blank=True)

    # provenance — what search context fed this question, for traceability
    source_context = models.TextField(blank=True)

    # dedup — vector stored as JSON list of floats (or swap to pgvector later)
    embedding = models.JSONField(null=True, blank=True)

    date_generated = models.DateField(auto_now_add=True, db_index=True)
    times_shown = models.PositiveIntegerField(default=0)
    user_rating = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )

    class Meta:
        ordering = ["-date_generated"]
        indexes = [
            models.Index(fields=["date_generated", "category"]),
        ]

    def __str__(self):
        return f"[{self.category}] {self.question[:60]}"
