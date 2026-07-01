from rest_framework.routers import DefaultRouter
from .views import DailyInterviewQuestionViewSet

router = DefaultRouter()
router.register("questions", DailyInterviewQuestionViewSet, basename="daily-question")

urlpatterns = router.urls
