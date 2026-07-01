from datetime import date
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import DailyInterviewQuestion
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
        qs = self.get_queryset().filter(date_generated=date.today())
        serializer = self.get_serializer(qs, many=True)
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
