from django.conf import settings
from django.db import models


class Task(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks')
	name = models.CharField(max_length=255)
	order = models.PositiveIntegerField(default=0)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	priority = models.CharField(max_length=10, choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')], default='medium')
	is_recurring = models.BooleanField(default=False)
	subtasks = models.JSONField(default=list, blank=True)

	class Meta:
		ordering = ['order', 'created_at', 'id']

	def __str__(self):
		return self.name


class DailyLog(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_logs')
	date = models.DateField()
	completed_tasks = models.ManyToManyField(Task, blank=True, related_name='daily_logs')
	journal_entry = models.TextField(blank=True, default='')
	is_frozen = models.BooleanField(default=False)
	metadata = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)


	class Meta:
		unique_together = ('user', 'date')
		ordering = ['-date', '-created_at']

	def __str__(self):
		return f'{self.user} - {self.date}'

	def get_completion_percentage(self):
		from django.utils import timezone
		from datetime import datetime, time, timedelta
		from django.db.models import Q
		
		today = timezone.localdate()
		tz = timezone.get_current_timezone()
		day_start = timezone.make_aware(datetime.combine(self.date, time.min), tz)
		day_end = day_start + timedelta(days=1)

		completed = self.completed_tasks.count()

		if self.date == today:
			active_today = self.user.tasks.filter(is_active=True).filter(
				Q(created_at__gte=day_start, created_at__lt=day_end) | Q(is_recurring=True, created_at__lt=day_end)
			)
			total_active = (active_today | self.completed_tasks.all()).distinct().count()
			if not total_active:
				return 0
			completed_today = self.completed_tasks.filter(is_active=True).count()
			return round((completed_today / total_active) * 100)
		else:
			if completed == 0:
				return None
			
			active_on_day = Task.objects.filter(user=self.user, is_active=True).filter(
				Q(created_at__gte=day_start, created_at__lt=day_end) | Q(is_recurring=True, created_at__lt=day_end)
			)
			total_active = (active_on_day | self.completed_tasks.all()).distinct().count()
			if not total_active:
				return 0
			return round((completed / total_active) * 100)


class Goal(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goals')
	title = models.CharField(max_length=255)
	is_completed = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	target_date = models.DateField(null=True, blank=True)

	class Meta:
		ordering = ['is_completed', '-created_at']

	def __str__(self):
		return self.title


class ContestStatus(models.TextChoices):
	UPCOMING = 'upcoming', 'Upcoming'
	LIVE = 'live', 'Live'
	ENDED = 'ended', 'Ended'
	CANCELLED = 'cancelled', 'Cancelled'


class ParticipationStatus(models.TextChoices):
	NOT_MARKED = 'not_marked', 'Not Marked'
	PARTICIPATED = 'participated', 'Participated'
	SKIPPED = 'skipped', 'Skipped'


class ReminderStatus(models.TextChoices):
	SCHEDULED = 'scheduled', 'Scheduled'
	SENT = 'sent', 'Sent'
	FAILED = 'failed', 'Failed'
	CANCELLED = 'cancelled', 'Cancelled'


class ReminderType(models.TextChoices):
	CONTEST = 'contest', 'Contest'
	TASK_DIGEST = 'task_digest', 'Task Digest'


class ContestEvent(models.Model):
	source_slug = models.CharField(max_length=64, db_index=True)
	source_name = models.CharField(max_length=128)
	source_key = models.CharField(max_length=255)
	title = models.CharField(max_length=255)
	url = models.URLField(max_length=500)
	start_time = models.DateTimeField(db_index=True)
	end_time = models.DateTimeField(db_index=True)
	duration_minutes = models.PositiveIntegerField(null=True, blank=True)
	timezone_name = models.CharField(max_length=64, default='Asia/Kolkata')
	status = models.CharField(max_length=16, choices=ContestStatus.choices, default=ContestStatus.UPCOMING)
	google_calendar_id = models.CharField(max_length=255, blank=True)
	google_event_id = models.CharField(max_length=255, blank=True)
	raw_data = models.JSONField(default=dict, blank=True)
	last_synced_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = ('source_slug', 'source_key')
		ordering = ['start_time', 'title']

	def __str__(self):
		return f'{self.source_name}: {self.title}'


class ContestParticipation(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contest_participations')
	contest = models.ForeignKey(ContestEvent, on_delete=models.CASCADE, related_name='participations')
	status = models.CharField(max_length=16, choices=ParticipationStatus.choices, default=ParticipationStatus.NOT_MARKED)
	marked_at = models.DateTimeField(null=True, blank=True)
	note = models.CharField(max_length=255, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = ('user', 'contest')
		ordering = ['-updated_at', '-created_at']

	def __str__(self):
		return f'{self.user} - {self.contest} - {self.status}'


class GoogleCalendarConnection(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='google_calendar_connection')
	google_email = models.EmailField(blank=True)
	access_token = models.TextField(blank=True)
	refresh_token = models.TextField(blank=True)
	token_expiry = models.DateTimeField(null=True, blank=True)
	scopes = models.JSONField(default=list, blank=True)
	calendar_id = models.CharField(max_length=255, default='primary')
	contest_sync_enabled = models.BooleanField(default=True)
	task_sync_enabled = models.BooleanField(default=False)
	is_connected = models.BooleanField(default=False)
	last_synced_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f'{self.user} calendar connection'


class ReminderEvent(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reminders')
	contest = models.ForeignKey(ContestEvent, on_delete=models.SET_NULL, null=True, blank=True, related_name='reminder_events')
	reminder_type = models.CharField(max_length=32, choices=ReminderType.choices)
	title = models.CharField(max_length=255)
	description = models.TextField(blank=True)
	reminder_at = models.DateTimeField(db_index=True)
	status = models.CharField(max_length=16, choices=ReminderStatus.choices, default=ReminderStatus.SCHEDULED)
	google_event_id = models.CharField(max_length=255, blank=True)
	payload = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['reminder_at', 'created_at']
		indexes = [models.Index(fields=['user', 'reminder_type', 'reminder_at'])]

	def __str__(self):
		return f'{self.user} - {self.title}'


class CodingProfile(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='coding_profile')
	leetcode_username = models.CharField(max_length=150, blank=True)
	codeforces_username = models.CharField(max_length=150, blank=True)
	codechef_username = models.CharField(max_length=150, blank=True)
	geeksforgeeks_username = models.CharField(max_length=150, blank=True)
	phone_number = models.CharField(max_length=30, blank=True)
	send_email_reminders = models.BooleanField(default=True)
	send_whatsapp_reminders = models.BooleanField(default=False)
	freeze_tokens = models.PositiveIntegerField(default=2)
	last_freeze_reset_month = models.DateField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f'{self.user.username} coding profile'


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_coding_profile(sender, instance, created, **kwargs):
	if created:
		CodingProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_coding_profile(sender, instance, **kwargs):
	if not hasattr(instance, 'coding_profile'):
		CodingProfile.objects.create(user=instance)
	instance.coding_profile.save()
