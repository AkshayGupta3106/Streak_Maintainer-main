from django.conf import settings
from django.db import models


class Task(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks')
	name = models.CharField(max_length=255)
	order = models.PositiveIntegerField(default=0)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['order', 'created_at', 'id']

	def __str__(self):
		return self.name


class DailyLog(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_logs')
	date = models.DateField()
	completed_tasks = models.ManyToManyField(Task, blank=True, related_name='daily_logs')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = ('user', 'date')
		ordering = ['-date', '-created_at']

	def __str__(self):
		return f'{self.user} - {self.date}'
