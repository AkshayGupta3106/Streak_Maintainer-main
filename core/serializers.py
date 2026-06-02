from django.contrib.auth.models import User
from rest_framework import serializers

from .models import DailyLog, Task


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ('id', 'name', 'order', 'is_active', 'created_at')
        read_only_fields = ('id', 'is_active', 'created_at')


class DailyLogSerializer(serializers.ModelSerializer):
    completed_task_ids = serializers.PrimaryKeyRelatedField(
        source='completed_tasks',
        many=True,
        queryset=Task.objects.none(),
        required=False,
    )
    completion_percentage = serializers.SerializerMethodField()

    class Meta:
        model = DailyLog
        fields = ('id', 'date', 'completed_task_ids', 'completion_percentage')
        read_only_fields = ('id', 'completion_percentage')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            self.fields['completed_task_ids'].queryset = Task.objects.filter(user=request.user)

    def get_completion_percentage(self, obj):
        active_tasks = getattr(obj, '_active_tasks_count', None)
        if active_tasks is None:
            active_tasks = obj.user.tasks.filter(is_active=True).count()
        if not active_tasks:
            return 0
        completed = obj.completed_tasks.filter(is_active=True).count()
        return round((completed / active_tasks) * 100)