from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DateLogView, HistoryView, LoginView, RefreshView, RegisterView, TaskViewSet, TodayLogView


router = DefaultRouter()
router.register('tasks', TaskViewSet, basename='task')

urlpatterns = [
	path('auth/register/', RegisterView.as_view(), name='register'),
	path('auth/login/', LoginView.as_view(), name='login'),
	path('auth/refresh/', RefreshView.as_view(), name='refresh'),
	path('logs/today/', TodayLogView.as_view(), name='today-log'),
	path('logs/history/', HistoryView.as_view(), name='history-log'),
	path('logs/<str:date_value>/', DateLogView.as_view(), name='date-log'),
]

urlpatterns += router.urls