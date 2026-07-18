from datetime import date
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import DailyInterviewQuestion, GenerationRun
from .serializers import DailyInterviewQuestionSerializer


class DailyInterviewQuestionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DailyInterviewQuestionSerializer
    permission_classes = [IsAuthenticated]
    queryset = DailyInterviewQuestion.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get("category")
        difficulty = self.request.query_params.get("difficulty")
        if category:
            qs = qs.filter(category=category)
        if difficulty:
            qs = qs.filter(difficulty=difficulty)
        return qs

    @action(detail=False, methods=["get"])
    def today(self, request):
        """GET /api/questions/today/ — today's batch of 10."""
        from django.utils import timezone
        today_local = date.today()
        today_utc = timezone.now().date()
        
        # Check if we have 10 or more questions in local date first, then fallback to UTC date.
        qs = self.get_queryset().filter(date_generated=today_local)
        if qs.count() < 10:
            qs_utc = self.get_queryset().filter(date_generated=today_utc)
            if qs_utc.count() >= 10:
                qs = qs_utc
                
        # If still less than 10 questions exist, trigger on-the-fly generation.
        if qs.count() < 10:
            # Check if there is already a recent pending, successful, or partial run today
            recent_run = GenerationRun.objects.filter(
                run_date=today_local,
                status__in=["success", "pending", "partial"]
            ).exists() or GenerationRun.objects.filter(
                run_date=today_utc,
                status__in=["success", "pending", "partial"]
            ).exists()
            
            if not recent_run:
                try:
                    from .tasks import generate_daily_questions
                    # Execute task synchronously
                    generate_daily_questions()
                    
                    # Re-query local first, then UTC
                    qs = self.get_queryset().filter(date_generated=today_local)
                    if qs.count() < 10:
                        qs = self.get_queryset().filter(date_generated=today_utc)
                except Exception:
                    pass
                    
        # Slice to exactly 10 questions to maintain the "batch of 10" constraint in the UI
        serializer = self.get_serializer(qs[:10], many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def rate(self, request, pk=None):
        """POST /api/questions/{id}/rate/  body: {"rating": 4}"""
        question = self.get_object()
        rating = request.data.get("rating")
        if rating not in range(1, 6):
            return Response({"error": "rating must be 1-5"}, status=status.HTTP_400_BAD_REQUEST)
        question.user_rating = rating
        question.times_shown += 1
        question.save(update_fields=["user_rating", "times_shown"])
        return Response(self.get_serializer(question).data)
