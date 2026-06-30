# Generated manually

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ContestEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_slug', models.CharField(db_index=True, max_length=64)),
                ('source_name', models.CharField(max_length=128)),
                ('source_key', models.CharField(max_length=255)),
                ('title', models.CharField(max_length=255)),
                ('url', models.URLField(max_length=500)),
                ('start_time', models.DateTimeField(db_index=True)),
                ('end_time', models.DateTimeField(db_index=True)),
                ('duration_minutes', models.PositiveIntegerField(blank=True, null=True)),
                ('timezone_name', models.CharField(default='Asia/Kolkata', max_length=64)),
                ('status', models.CharField(choices=[('upcoming', 'Upcoming'), ('live', 'Live'), ('ended', 'Ended'), ('cancelled', 'Cancelled')], default='upcoming', max_length=16)),
                ('google_calendar_id', models.CharField(blank=True, max_length=255)),
                ('google_event_id', models.CharField(blank=True, max_length=255)),
                ('raw_data', models.JSONField(blank=True, default=dict)),
                ('last_synced_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['start_time', 'title'],
                'unique_together': {('source_slug', 'source_key')},
            },
        ),
        migrations.CreateModel(
            name='GoogleCalendarConnection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('google_email', models.EmailField(blank=True, max_length=254)),
                ('access_token', models.TextField(blank=True)),
                ('refresh_token', models.TextField(blank=True)),
                ('token_expiry', models.DateTimeField(blank=True, null=True)),
                ('scopes', models.JSONField(blank=True, default=list)),
                ('calendar_id', models.CharField(default='primary', max_length=255)),
                ('contest_sync_enabled', models.BooleanField(default=True)),
                ('task_sync_enabled', models.BooleanField(default=False)),
                ('is_connected', models.BooleanField(default=False)),
                ('last_synced_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='google_calendar_connection', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='CodingProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('leetcode_username', models.CharField(blank=True, max_length=150)),
                ('codeforces_username', models.CharField(blank=True, max_length=150)),
                ('codechef_username', models.CharField(blank=True, max_length=150)),
                ('geeksforgeeks_username', models.CharField(blank=True, max_length=150)),
                ('phone_number', models.CharField(blank=True, max_length=30)),
                ('send_email_reminders', models.BooleanField(default=True)),
                ('send_whatsapp_reminders', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='coding_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ContestParticipation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('not_marked', 'Not Marked'), ('participated', 'Participated'), ('skipped', 'Skipped')], default='not_marked', max_length=16)),
                ('marked_at', models.DateTimeField(blank=True, null=True)),
                ('note', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('contest', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participations', to='core.contestevent')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contest_participations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at', '-created_at'],
                'unique_together': {('user', 'contest')},
            },
        ),
        migrations.CreateModel(
            name='ReminderEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reminder_type', models.CharField(choices=[('contest', 'Contest'), ('task_digest', 'Task Digest')], max_length=32)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('reminder_at', models.DateTimeField(db_index=True)),
                ('status', models.CharField(choices=[('scheduled', 'Scheduled'), ('sent', 'Sent'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='scheduled', max_length=16)),
                ('google_event_id', models.CharField(blank=True, max_length=255)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('contest', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reminder_events', to='core.contestevent')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reminders', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['reminder_at', 'created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='reminderevent',
            index=models.Index(fields=['user', 'reminder_type', 'reminder_at'], name='core_remind_user_id_453d86_idx'),
        ),
    ]
