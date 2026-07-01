from rest_framework import serializers
from .models import DailyInterviewQuestion


class DailyInterviewQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyInterviewQuestion
        fields = [
            "id", "question", "category", "difficulty", "company_style",
            "model_answer", "follow_up_questions", "date_generated",
            "times_shown", "user_rating", "source_context",
        ]
        read_only_fields = ["id", "date_generated"]
