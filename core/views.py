from datetime import date as date_type

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import DailyLog, Task
from .serializers import DailyLogSerializer, TaskSerializer, UserSerializer


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '')

        if not username or not email or not password:
            return Response(
                {'detail': 'username, email, and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username=username).exists():
            return Response({'detail': 'Username is already taken.'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({'detail': 'Email is already registered.'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, email=email, password=password)
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user, is_active=True)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])


def _serialize_log(log):
    log._active_tasks_count = log.user.tasks.filter(is_active=True).count()
    serializer = DailyLogSerializer(log)
    tasks = Task.objects.filter(user=log.user, is_active=True) | log.completed_tasks.all()
    tasks = tasks.distinct().order_by('order', 'created_at', 'id')
    return {
        **serializer.data,
        'tasks': TaskSerializer(tasks, many=True).data,
    }


def _get_or_create_log(user, target_date):
    log, _ = DailyLog.objects.get_or_create(user=user, date=target_date)
    return log


def _set_completed_tasks(log, request):
    raw_task_ids = request.data.get('completed_task_ids')
    if raw_task_ids is None:
        return

    if not isinstance(raw_task_ids, list):
        raise ValueError('completed_task_ids must be a list.')

    task_ids = []
    for task_id in raw_task_ids:
        try:
            task_ids.append(int(task_id))
        except (TypeError, ValueError):
            raise ValueError('completed_task_ids must contain only valid task ids.')

    completed_tasks = Task.objects.filter(user=request.user, is_active=True, id__in=task_ids)
    log.completed_tasks.set(completed_tasks)
    log.save()


class TodayLogView(APIView):
    def get(self, request):
        today = timezone.localdate()
        log = _get_or_create_log(request.user, today)
        return Response(_serialize_log(log))

    def post(self, request):
        return self._save(request)

    def put(self, request):
        return self._save(request)

    def patch(self, request):
        return self._save(request)

    def _save(self, request):
        today = timezone.localdate()
        log = _get_or_create_log(request.user, today)
        try:
            _set_completed_tasks(log, request)
        except ValueError as error:
            return Response({'completed_task_ids': [str(error)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_serialize_log(log))


class DateLogView(APIView):
    def get_object(self, request, date_value):
        target_date = date_type.fromisoformat(date_value)
        return _get_or_create_log(request.user, target_date)

    def get(self, request, date_value):
        log = self.get_object(request, date_value)
        return Response(_serialize_log(log))

    def put(self, request, date_value):
        log = self.get_object(request, date_value)
        try:
            _set_completed_tasks(log, request)
        except ValueError as error:
            return Response({'completed_task_ids': [str(error)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_serialize_log(log))

    def patch(self, request, date_value):
        log = self.get_object(request, date_value)
        try:
            _set_completed_tasks(log, request)
        except ValueError as error:
            return Response({'completed_task_ids': [str(error)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_serialize_log(log))


class HistoryView(APIView):
    def get(self, request):
        active_task_count = request.user.tasks.filter(is_active=True).count()
        payload = []
        for log in DailyLog.objects.filter(user=request.user).order_by('-date'):
            log._active_tasks_count = active_task_count
            payload.append(
                {
                    'id': log.id,
                    'date': log.date,
                    'completion_percentage': DailyLogSerializer(log).data['completion_percentage'],
                }
            )
        return Response(payload)

