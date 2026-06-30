from datetime import date as date_type

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import DailyLog, Task, Goal
from .serializers import DailyLogSerializer, TaskSerializer, UserSerializer, GoalSerializer


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        name = request.data.get('name', '').strip()
        password = request.data.get('password', '')

        if not username or not name or not password:
            return Response(
                {'detail': 'username, name, and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username=username).exists():
            return Response({'detail': 'Username is already taken.'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, password=password)
        user.first_name = name
        user.save(update_fields=['first_name'])
        
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

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            username = request.data.get('username')
            try:
                user = User.objects.get(username=username)
                response.data['user'] = UserSerializer(user).data
            except User.DoesNotExist:
                pass
        return response


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]


class GoogleAuthView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        action = request.data.get('action')
        token = request.data.get('token')
        username = request.data.get('username', '').strip()

        if not token:
            return Response({'detail': 'Google token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Call Google API to get user info
        import requests
        try:
            response = requests.get('https://www.googleapis.com/oauth2/v3/userinfo', headers={
                'Authorization': f'Bearer {token}'
            }, timeout=10)
            if response.status_code != 200:
                return Response({'detail': 'Invalid Google token.'}, status=status.HTTP_400_BAD_REQUEST)
            google_user = response.json()
        except requests.RequestException:
            return Response({'detail': 'Failed to connect to Google for authentication.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        email = google_user.get('email', '').strip().lower()
        name = google_user.get('name', '').strip() or google_user.get('given_name', '').strip()

        if not email:
            return Response({'detail': 'Failed to retrieve email from Google.'}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'login':
            try:
                user = User.objects.get(email=email)
                refresh = RefreshToken.for_user(user)
                return Response({
                    'user': UserSerializer(user).data,
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                })
            except User.DoesNotExist:
                return Response(
                    {
                        'detail': f'No account found with email {email}. Please register first.',
                        'email': email,
                        'name': name
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

        elif action == 'register':
            if not username:
                return Response({'detail': 'Username is required.'}, status=status.HTTP_400_BAD_REQUEST)

            if User.objects.filter(email=email).exists():
                return Response({'detail': 'An account with this email already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            if User.objects.filter(username=username).exists():
                return Response({'detail': 'Username is already taken.'}, status=status.HTTP_400_BAD_REQUEST)

            user = User.objects.create_user(username=username, email=email)
            user.first_name = name
            user.set_unusable_password()
            user.save()

            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_201_CREATED)

        return Response({'detail': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        from datetime import datetime, time, timedelta
        from django.db.models import Q
        today = timezone.localdate()
        tz = timezone.get_current_timezone()
        day_start = timezone.make_aware(datetime.combine(today, time.min), tz)
        day_end = day_start + timedelta(days=1)
        return Task.objects.filter(
            user=self.request.user,
            is_active=True
        ).filter(
            Q(created_at__gte=day_start, created_at__lt=day_end) | Q(is_recurring=True, created_at__lt=day_end)
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active'])


class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


def apply_automatic_freezes(user):
    from django.utils import timezone
    from datetime import timedelta
    
    today = timezone.localdate()
    profile = user.coding_profile
    
    # Reset freeze tokens if new month
    current_month_start = today.replace(day=1)
    if not profile.last_freeze_reset_month or profile.last_freeze_reset_month < current_month_start:
        profile.freeze_tokens = 2
        profile.last_freeze_reset_month = current_month_start
        profile.save()
        
    logs = {log.date: log for log in DailyLog.objects.filter(user=user)}
    if not logs:
        return
        
    sorted_dates = sorted(logs.keys())
    first_date = sorted_dates[0]
    yesterday = today - timedelta(days=1)
    
    current_date = first_date
    while current_date <= yesterday:
        log = logs.get(current_date)
        is_success = False
        
        if log:
            if log.is_frozen:
                is_success = True
            else:
                pct = log.get_completion_percentage()
                if pct is not None and pct >= 100:
                    is_success = True
                    
        if not is_success:
            if profile.freeze_tokens > 0:
                if not log:
                    log = DailyLog.objects.create(user=user, date=current_date)
                    logs[current_date] = log
                log.is_frozen = True
                log.save()
                profile.freeze_tokens -= 1
                profile.save()
                is_success = True
                
        current_date += timedelta(days=1)


def calculate_user_streaks(user):
    from django.utils import timezone
    from datetime import timedelta
    
    apply_automatic_freezes(user)
    
    logs = {log.date: log for log in DailyLog.objects.filter(user=user)}
    if not logs:
        return {'current_streak': 0, 'longest_streak': 0}
        
    sorted_dates = sorted(logs.keys())
    first_date = sorted_dates[0]
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    
    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    
    current_date = first_date
    while current_date <= today:
        log = logs.get(current_date)
        is_success = False
        
        if log:
            if log.is_frozen:
                is_success = True
            else:
                pct = log.get_completion_percentage()
                if pct is not None and pct >= 100:
                    is_success = True
                    
        if is_success:
            temp_streak += 1
            if temp_streak > longest_streak:
                longest_streak = temp_streak
        else:
            if current_date == today:
                pass
            else:
                temp_streak = 0
                
        current_date += timedelta(days=1)
        
    yesterday_log = logs.get(yesterday)
    yesterday_success = False
    if yesterday_log:
        if yesterday_log.is_frozen:
            yesterday_success = True
        else:
            pct = yesterday_log.get_completion_percentage()
            if pct is not None and pct >= 100:
                yesterday_success = True
                
    today_log = logs.get(today)
    today_success = False
    if today_log:
        if today_log.is_frozen:
            today_success = True
        else:
            pct = today_log.get_completion_percentage()
            if pct is not None and pct >= 100:
                today_success = True
                
    if today_success:
        current_streak = temp_streak
    elif yesterday_success:
        current_streak = temp_streak
    else:
        current_streak = 0
        
    return {
        'current_streak': current_streak,
        'longest_streak': max(longest_streak, current_streak)
    }


def _serialize_log(log):
    from django.utils import timezone
    from datetime import datetime, time, timedelta
    from django.db.models import Q
    
    today = timezone.localdate()
    tz = timezone.get_current_timezone()
    day_start = timezone.make_aware(datetime.combine(log.date, time.min), tz)
    day_end = day_start + timedelta(days=1)

    serializer = DailyLogSerializer(log)
    completed_count = log.completed_tasks.count()

    if log.date == today:
        active_on_day = Task.objects.filter(user=log.user, is_active=True).filter(
            Q(created_at__gte=day_start, created_at__lt=day_end) | Q(is_recurring=True, created_at__lt=day_end)
        )
        tasks = active_on_day | log.completed_tasks.all()
        tasks = tasks.distinct().order_by('order', 'created_at', 'id')
        tasks_data = TaskSerializer(tasks, many=True).data
    else:
        if completed_count == 0:
            tasks_data = []
        else:
            active_on_day = Task.objects.filter(user=log.user, is_active=True).filter(
                Q(created_at__gte=day_start, created_at__lt=day_end) | Q(is_recurring=True, created_at__lt=day_end)
            )
            tasks = active_on_day | log.completed_tasks.all()
            tasks = tasks.distinct().order_by('order', 'created_at', 'id')
            tasks_data = TaskSerializer(tasks, many=True).data

    # Check reset of freeze tokens (2 per month)
    profile = log.user.coding_profile
    current_month_start = today.replace(day=1)
    if not profile.last_freeze_reset_month or profile.last_freeze_reset_month < current_month_start:
        profile.freeze_tokens = 2
        profile.last_freeze_reset_month = current_month_start
        profile.save()

    streaks = calculate_user_streaks(log.user)

    return {
        **serializer.data,
        'tasks': tasks_data,
        'journal_entry': log.journal_entry,
        'is_frozen': log.is_frozen,
        'current_streak': streaks['current_streak'],
        'longest_streak': streaks['longest_streak'],
        'freeze_tokens': profile.freeze_tokens,
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


def _update_log_details(log, request):
    from django.utils import timezone
    today = timezone.localdate()
    if log.date != today:
        if 'completed_task_ids' in request.data or 'journal_entry' in request.data or 'is_frozen' in request.data:
            raise ValueError("Edits are only allowed for today's log.")

    _set_completed_tasks(log, request)

    if 'journal_entry' in request.data:
        log.journal_entry = request.data['journal_entry']
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
            _update_log_details(log, request)
        except ValueError as error:
            return Response({'error': str(error), 'completed_task_ids': [str(error)]}, status=status.HTTP_400_BAD_REQUEST)
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
            _update_log_details(log, request)
        except ValueError as error:
            return Response({'error': str(error), 'completed_task_ids': [str(error)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_serialize_log(log))

    def patch(self, request, date_value):
        log = self.get_object(request, date_value)
        try:
            _update_log_details(log, request)
        except ValueError as error:
            return Response({'error': str(error), 'completed_task_ids': [str(error)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_serialize_log(log))


class HistoryView(APIView):
    def get(self, request):
        apply_automatic_freezes(request.user)
        payload = []
        for log in DailyLog.objects.filter(user=request.user).order_by('-date'):
            payload.append(
                {
                    'id': log.id,
                    'date': log.date,
                    'completion_percentage': log.get_completion_percentage(),
                    'is_frozen': log.is_frozen,
                    'journal_entry': log.journal_entry,
                }
            )
        return Response(payload)


from .models import CodingProfile, ContestEvent
from .serializers import CodingProfileSerializer, ContestEventSerializer
import threading
from core.services.sync_engine import run_contest_sync

class CodingProfileView(APIView):
    def get_object(self, request):
        profile, created = CodingProfile.objects.get_or_create(user=request.user)
        return profile

    def get(self, request):
        profile = self.get_object(request)
        serializer = CodingProfileSerializer(profile)
        return Response(serializer.data)

    def put(self, request):
        return self._save(request)

    def patch(self, request):
        return self._save(request)

    def _save(self, request):
        profile = self.get_object(request)
        serializer = CodingProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Clear profile stats cache since coding profile has changed
            from django.core.cache import cache
            lc_user = (profile.leetcode_username or '').strip().lower()
            cf_user = (profile.codeforces_username or '').strip().lower()
            cache_key = f"profile_stats_{profile.id}_{lc_user}_{cf_user}"
            cache.delete(cache_key)

            # Trigger background sync when profile changes
            threading.Thread(target=run_contest_sync, daemon=True).start()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ContestListView(APIView):
    def get(self, request):
        profile, created = CodingProfile.objects.get_or_create(user=request.user)
        platforms = []
        if profile.leetcode_username:
            platforms.append('leetcode')
        if profile.codeforces_username:
            platforms.append('codeforces')
        if profile.codechef_username:
            platforms.append('codechef')
        if profile.geeksforgeeks_username:
            platforms.append('geeksforgeeks')

        if not platforms:
            return Response([])

        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        five_days_ahead = now + timedelta(days=5)
        
        contests = ContestEvent.objects.filter(
            source_slug__in=platforms,
            status='upcoming',
            start_time__gt=now,
            start_time__lte=five_days_ahead
        ).order_by('start_time')

        serializer = ContestEventSerializer(contests, many=True)
        return Response(serializer.data)


from core.services.profile_stats import get_profile_stats

class CodingProfileStatsView(APIView):
    def get(self, request):
        profile, created = CodingProfile.objects.get_or_create(user=request.user)
        stats = get_profile_stats(profile)
        return Response(stats)


class DailyQuoteView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        import requests
        import random
        try:
            res = requests.get('https://favqs.com/api/qotd', timeout=4)
            if res.status_code == 200:
                data = res.json()
                if data and 'quote' in data and 'body' in data['quote']:
                    return Response({
                        'text': data['quote']['body'],
                        'author': data['quote']['author'] or 'Unknown'
                    })
        except Exception:
            pass

        fallbacks = [
            {"text": "Consistency beats intensity when the goal is lasting change.", "author": "James Clear"},
            {"text": "Clean code always looks like it was written by someone who cares.", "author": "Michael Feathers"},
            {"text": "Small wins compound into strong streaks.", "author": "James Clear"},
            {"text": "One honest day is better than a perfect plan you never start.", "author": "Unknown"},
            {"text": "Focus on progress, not perfection.", "author": "Bill Gates"},
            {"text": "The secret of getting ahead is getting started.", "author": "Mark Twain"},
            {"text": "First, solve the problem. Then, write the code.", "author": "John Johnson"},
            {"text": "Quality is not an act, it is a habit.", "author": "Aristotle"}
        ]
        return Response(random.choice(fallbacks))

