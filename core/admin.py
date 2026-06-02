from django.contrib import admin

from .models import DailyLog, Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
	list_display = ('name', 'user', 'order', 'is_active', 'created_at')
	list_filter = ('is_active', 'created_at')
	search_fields = ('name', 'user__username', 'user__email')


@admin.register(DailyLog)
class DailyLogAdmin(admin.ModelAdmin):
	list_display = ('user', 'date', 'created_at', 'updated_at')
	list_filter = ('date',)
	search_fields = ('user__username', 'user__email')
