import logging
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import close_old_connections, transaction
from django.core.exceptions import ObjectDoesNotExist

from core.models import ContestEvent, ReminderEvent, CodingProfile
from core.services.contest_sources import fetch_all_contests
from core.services.google_calendar import sync_calendar_event, contest_calendar_payload
from core.services.notifications import send_email_reminder

logger = logging.getLogger(__name__)

def run_contest_sync():
    close_old_connections()
    logger.info("Starting contest sync from platforms...")
    try:
        snapshots = fetch_all_contests()
    except Exception as e:
        logger.error(f"Error fetching contests from sources: {e}")
        return
        
    synced_count = 0
    try:
        with transaction.atomic():
            for snap in snapshots:
                contest, created = ContestEvent.objects.update_or_create(
                    source_slug=snap.source_slug,
                    source_key=snap.source_key,
                    defaults={
                        'source_name': snap.source_name,
                        'title': snap.title,
                        'url': snap.url,
                        'start_time': snap.start_time,
                        'end_time': snap.end_time,
                        'duration_minutes': snap.duration_minutes,
                        'status': snap.status,
                        'raw_data': snap.raw_data,
                    }
                )
                synced_count += 1
    except Exception as tx_err:
        logger.error(f"Error saving synced contests to database: {tx_err}")
        
    logger.info(f"Successfully synced {synced_count} contests.")
    
    users = User.objects.all()
    now = timezone.now()
    for user in users:
        try:
            profile = user.coding_profile
        except ObjectDoesNotExist:
            profile = CodingProfile.objects.create(user=user)
            
        connected_platforms = []
        if profile.leetcode_username:
            connected_platforms.append('leetcode')
        if profile.codeforces_username:
            connected_platforms.append('codeforces')
        if profile.codechef_username:
            connected_platforms.append('codechef')
        if profile.geeksforgeeks_username:
            connected_platforms.append('geeksforgeeks')
            
        if not connected_platforms:
            continue
            
        upcoming_contests = ContestEvent.objects.filter(
            source_slug__in=connected_platforms,
            status='upcoming',
            start_time__gt=now
        )
        
        for contest in upcoming_contests:
            # 1. Schedule backend ReminderEvent
            reminder_time = contest.start_time - timedelta(hours=1)
            if reminder_time > now:
                if profile.send_email_reminders:
                    # We check if reminder already exists
                    reminder, created = ReminderEvent.objects.get_or_create(
                        user=user,
                        contest=contest,
                        reminder_type='contest',
                        defaults={
                            'title': f"Upcoming: {contest.title}",
                            'description': f"Contest {contest.title} on {contest.source_name} starts in 1 hour!",
                            'reminder_at': reminder_time,
                            'status': 'scheduled',
                        }
                    )
                    
            # 2. Sync to Google Calendar if connection is active
            if hasattr(user, 'google_calendar_connection') and user.google_calendar_connection.is_connected:
                connection = user.google_calendar_connection
                if connection.contest_sync_enabled:
                    try:
                        payload = contest_calendar_payload(contest, reminder_minutes=60)
                        sync_calendar_event(connection, payload)
                    except Exception as gcal_err:
                        logger.error(f"Failed to sync contest {contest.title} to Google Calendar for {user.username}: {gcal_err}")

def run_reminder_dispatch():
    close_old_connections()
    now = timezone.now()
    due_reminders = ReminderEvent.objects.filter(
        status='scheduled',
        reminder_at__lte=now
    )
    
    if not due_reminders.exists():
        return
        
    logger.info(f"Dispatching {due_reminders.count()} due reminders...")
    
    for reminder in due_reminders:
        user = reminder.user
        contest = reminder.contest
        if not contest:
            reminder.status = 'failed'
            reminder.save(update_fields=['status'])
            continue
            
        try:
            profile = user.coding_profile
        except ObjectDoesNotExist:
            reminder.status = 'failed'
            reminder.save(update_fields=['status'])
            continue
            
        email_success = False
        
        send_email = profile.send_email_reminders
        
        if send_email and user.email:
            email_success = send_email_reminder(
                email_address=user.email,
                username=user.username,
                contest_title=contest.title,
                source_name=contest.source_name,
                start_time=contest.start_time,
                contest_url=contest.url
            )
        else:
            email_success = True
            
        if email_success:
            reminder.status = 'sent'
        else:
            reminder.status = 'failed'
            
        reminder.save(update_fields=['status', 'updated_at'])
