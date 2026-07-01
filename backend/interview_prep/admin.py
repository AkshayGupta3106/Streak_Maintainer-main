from django.contrib import admin
from .models import DailyInterviewQuestion, GenerationRun


@admin.register(GenerationRun)
class GenerationRunAdmin(admin.ModelAdmin):
    list_display = ("run_date", "status", "llm_provider_used", "questions_generated", "questions_rejected_duplicate")
    list_filter = ("status", "llm_provider_used", "run_date")
    readonly_fields = ("id", "created_at")


@admin.register(DailyInterviewQuestion)
class DailyInterviewQuestionAdmin(admin.ModelAdmin):
    list_display = ("question_short", "category", "difficulty", "date_generated", "times_shown", "user_rating")
    list_filter = ("category", "difficulty", "date_generated")
    search_fields = ("question", "model_answer")
    readonly_fields = ("id", "embedding")  # embedding is machine-generated, hide from manual edit

    def question_short(self, obj):
        return obj.question[:70]
    question_short.short_description = "Question"
