from django.contrib.auth.models import User
from rest_framework import serializers

from .models import DailyLog, Task, CodingProfile, ContestEvent, Goal


class CodingProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodingProfile
        fields = (
            'id',
            'leetcode_username',
            'codeforces_username',
            'codechef_username',
            'geeksforgeeks_username',
            'phone_number',
            'send_email_reminders',
            'send_whatsapp_reminders',
        )


class UserSerializer(serializers.ModelSerializer):
    coding_profile = CodingProfileSerializer(read_only=True)
    name = serializers.CharField(source='first_name', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'name', 'email', 'coding_profile')


class ContestEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContestEvent
        fields = (
            'id',
            'source_slug',
            'source_name',
            'source_key',
            'title',
            'url',
            'start_time',
            'end_time',
            'duration_minutes',
            'status',
        )


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ('id', 'name', 'order', 'is_active', 'created_at', 'priority', 'is_recurring', 'subtasks')
        read_only_fields = ('id', 'is_active', 'created_at')


class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = ('id', 'title', 'is_completed', 'created_at', 'target_date')
        read_only_fields = ('id', 'created_at')


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
        fields = ('id', 'date', 'completed_task_ids', 'completion_percentage', 'journal_entry', 'is_frozen', 'metadata')
        read_only_fields = ('id', 'completion_percentage')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            self.fields['completed_task_ids'].queryset = Task.objects.filter(user=request.user)

    def get_completion_percentage(self, obj):
        return obj.get_completion_percentage()