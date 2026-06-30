import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

def send_email_reminder(email_address: str, username: str, contest_title: str, source_name: str, start_time, contest_url: str):
    if not email_address:
        return False
        
    subject = f"Reminder: Upcoming Contest - {contest_title}"
    start_str = start_time.strftime('%I:%M %p %Z, %d %B %Y')
    
    html_message = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2>Upcoming Contest Reminder!</h2>
        <p>Hey <strong>{username}</strong>,</p>
        <p>This is a reminder that the contest <strong>{contest_title}</strong> on <strong>{source_name}</strong> is starting in <strong>1 hour</strong>!</p>
        <p><strong>Start Time:</strong> {start_str}</p>
        <p>Make sure you are ready. You can access the contest link below:</p>
        <p><a href="{contest_url}" style="display: inline-block; padding: 10px 20px; background-color: #8bd17c; color: #081120; text-decoration: none; border-radius: 5px; font-weight: bold;">Go to Contest</a></p>
        <br/>
        <p>Good luck!</p>
      </body>
    </html>
    """
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject,
            plain_message,
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@streak-maintainer.local'),
            [email_address],
            html_message=html_message,
            fail_silently=False
        )
        logger.info(f"Contest reminder email sent to {email_address} for contest: {contest_title}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {email_address}: {e}")
        return False

