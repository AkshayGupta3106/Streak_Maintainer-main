from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
	DateLogView, HistoryView, LoginView, RefreshView, RegisterView,
	TaskViewSet, TodayLogView, CodingProfileView, ContestListView, CodingProfileStatsView,
	GoogleAuthView, GoalViewSet, DailyQuoteView
)


router = DefaultRouter()
router.register('tasks', TaskViewSet, basename='task')
router.register('goals', GoalViewSet, basename='goal')

urlpatterns = [
	path('auth/register/', RegisterView.as_view(), name='register'),
	path('auth/login/', LoginView.as_view(), name='login'),
	path('auth/refresh/', RefreshView.as_view(), name='refresh'),
	path('auth/google/', GoogleAuthView.as_view(), name='google-auth'),
	path('logs/today/', TodayLogView.as_view(), name='today-log'),
	path('logs/history/', HistoryView.as_view(), name='history-log'),
	path('logs/<str:date_value>/', DateLogView.as_view(), name='date-log'),
	path('profile/coding/', CodingProfileView.as_view(), name='coding-profile'),
	path('profile/coding/stats/', CodingProfileStatsView.as_view(), name='coding-profile-stats'),
	path('contests/', ContestListView.as_view(), name='contest-list'),
	path('quote/', DailyQuoteView.as_view(), name='daily-quote'),
]

urlpatterns += router.urls