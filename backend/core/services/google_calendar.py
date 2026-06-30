from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import os
from typing import Any

import requests
from django.conf import settings
from django.core import signing
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from django.utils.text import slugify
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.models import GoogleCalendarConnection


GOOGLE_SCOPES = ['https://www.googleapis.com/auth/calendar.events']
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'
GOOGLE_TOKEN_URI = 'https://oauth2.googleapis.com/token'
CALENDAR_TIMEZONE = 'Asia/Kolkata'
STATE_SALT = 'google-calendar-oauth-state'
EVENT_ID_PREFIX = 'streak'


@dataclass(frozen=True)
class GoogleCalendarPayload:
    event_id: str
    summary: str
    description: str
    start_time: datetime
    end_time: datetime
    reminder_minutes: int | None
    metadata: dict[str, Any]
    cancelled: bool = False


def _get_google_client_config() -> dict[str, Any]:
    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
    client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '')
    redirect_uri = getattr(settings, 'GOOGLE_REDIRECT_URI', '')

    if not client_id or not client_secret or not redirect_uri:
        raise ImproperlyConfigured('Google OAuth settings are not configured.')

    return {
        'web': {
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uris': [redirect_uri],
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': GOOGLE_TOKEN_URI,
        }
    }


def has_google_oauth_config() -> bool:
    return bool(
        getattr(settings, 'GOOGLE_CLIENT_ID', '')
        and getattr(settings, 'GOOGLE_CLIENT_SECRET', '')
        and getattr(settings, 'GOOGLE_REDIRECT_URI', '')
    )


def build_oauth_state(user, next_url: str | None = None) -> str:
    return signing.dumps(
        {
            'user_id': user.id,
            'next_url': next_url or getattr(settings, 'FRONTEND_APP_URL', '/'),
        },
        salt=STATE_SALT,
    )


def parse_oauth_state(state: str) -> dict[str, Any]:
    return signing.loads(state, salt=STATE_SALT)


def build_authorization_url(user, next_url: str | None = None) -> str:
    flow = Flow.from_client_config(_get_google_client_config(), scopes=GOOGLE_SCOPES)
    flow.redirect_uri = getattr(settings, 'GOOGLE_REDIRECT_URI', '')
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=build_oauth_state(user, next_url=next_url),
    )
    return auth_url


def _credentials_from_connection(connection: GoogleCalendarConnection) -> Credentials:
    credentials = Credentials(
        token=connection.access_token or None,
        refresh_token=connection.refresh_token or None,
        token_uri=GOOGLE_TOKEN_URI,
        client_id=getattr(settings, 'GOOGLE_CLIENT_ID', ''),
        client_secret=getattr(settings, 'GOOGLE_CLIENT_SECRET', ''),
        scopes=connection.scopes or GOOGLE_SCOPES,
    )
    if connection.token_expiry:
        credentials.expiry = connection.token_expiry
    return credentials


def _build_calendar_service(connection: GoogleCalendarConnection):
    credentials = _credentials_from_connection(connection)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        connection.access_token = credentials.token or ''
        if credentials.refresh_token:
            connection.refresh_token = credentials.refresh_token
        connection.token_expiry = credentials.expiry
        connection.save(update_fields=['access_token', 'refresh_token', 'token_expiry', 'updated_at'])

    return build('calendar', 'v3', credentials=credentials, cache_discovery=False)


def _event_id_for_key(key: str) -> str:
    normalized_key = slugify(key).replace('-', '_')
    return f'{EVENT_ID_PREFIX}_{normalized_key}'[:1024]


def _build_event_body(payload: GoogleCalendarPayload) -> dict[str, Any]:
    return {
        'id': payload.event_id,
        'summary': payload.summary,
        'description': payload.description,
        'start': {
            'dateTime': payload.start_time.isoformat(),
            'timeZone': CALENDAR_TIMEZONE,
        },
        'end': {
            'dateTime': payload.end_time.isoformat(),
            'timeZone': CALENDAR_TIMEZONE,
        },
        'reminders': {
            'useDefault': False,
            'overrides': (
                []
                if payload.reminder_minutes is None
                else [
                    {'method': 'popup', 'minutes': payload.reminder_minutes},
                    {'method': 'email', 'minutes': payload.reminder_minutes},
                ]
            ),
        },
        'extendedProperties': {
            'private': {key: str(value) for key, value in payload.metadata.items()},
        },
    }


def sync_calendar_event(connection: GoogleCalendarConnection, payload: GoogleCalendarPayload) -> dict[str, Any] | None:
    if not connection.is_connected:
        return None

    service = _build_calendar_service(connection)
    calendar_id = connection.calendar_id or 'primary'

    if payload.cancelled:
        try:
            service.events().delete(calendarId=calendar_id, eventId=payload.event_id, sendUpdates='all').execute()
        except HttpError as error:
            if error.resp.status != 404:
                raise
        return None

    event_body = _build_event_body(payload)

    try:
        result = service.events().insert(calendarId=calendar_id, body=event_body, sendUpdates='all').execute()
    except HttpError as error:
        if error.resp.status in {409, 412}:
            result = service.events().update(calendarId=calendar_id, eventId=payload.event_id, body=event_body, sendUpdates='all').execute()
        elif error.resp.status == 404:
            result = service.events().insert(calendarId=calendar_id, body=event_body, sendUpdates='all').execute()
        else:
            raise

    connection.last_synced_at = timezone.now()
    connection.save(update_fields=['last_synced_at', 'updated_at'])
    return result


def save_google_connection_from_state(state: str, code: str) -> GoogleCalendarConnection:
    state_payload = parse_oauth_state(state)
    user_id = state_payload['user_id']
    flow = Flow.from_client_config(_get_google_client_config(), scopes=GOOGLE_SCOPES)
    flow.redirect_uri = getattr(settings, 'GOOGLE_REDIRECT_URI', '')
    flow.fetch_token(code=code)
    credentials = flow.credentials

    google_email = ''
    try:
        response = requests.get(GOOGLE_USERINFO_URL, headers={'Authorization': f'Bearer {credentials.token}'}, timeout=20)
        if response.ok:
            google_email = response.json().get('email', '')
    except requests.RequestException:
        google_email = ''

    connection, _ = GoogleCalendarConnection.objects.update_or_create(
        user_id=user_id,
        defaults={
            'google_email': google_email,
            'access_token': credentials.token or '',
            'refresh_token': credentials.refresh_token or '',
            'token_expiry': credentials.expiry,
            'scopes': list(credentials.scopes or GOOGLE_SCOPES),
            'calendar_id': 'primary',
            'contest_sync_enabled': True,
            'task_sync_enabled': True,
            'is_connected': True,
        },
    )
    return connection


def disconnect_google_connection(connection: GoogleCalendarConnection) -> None:
    connection.access_token = ''
    connection.refresh_token = ''
    connection.token_expiry = None
    connection.scopes = []
    connection.is_connected = False
    connection.last_synced_at = timezone.now()
    connection.save(update_fields=['access_token', 'refresh_token', 'token_expiry', 'scopes', 'is_connected', 'last_synced_at', 'updated_at'])


def contest_calendar_payload(contest, reminder_minutes: int = 10) -> GoogleCalendarPayload:
    return GoogleCalendarPayload(
        event_id=_event_id_for_key(f'{contest.source_slug}-{contest.source_key}'),
        summary=f'{contest.title} ({contest.source_name})',
        description=f'Contest source: {contest.source_name}\nURL: {contest.url}\nStatus: {contest.status}',
        start_time=contest.start_time,
        end_time=contest.end_time,
        reminder_minutes=reminder_minutes,
        metadata={
            'source_slug': contest.source_slug,
            'source_key': contest.source_key,
            'source_name': contest.source_name,
            'contest_id': contest.id,
        },
        cancelled=contest.status == 'cancelled',
    )


def task_digest_calendar_payload(user, date_value, summary: str, description: str, start_time: datetime, end_time: datetime) -> GoogleCalendarPayload:
    return GoogleCalendarPayload(
        event_id=_event_id_for_key(f'task-digest-{user.id}-{date_value.isoformat()}'),
        summary=summary,
        description=description,
        start_time=start_time,
        end_time=end_time,
        reminder_minutes=0,
        metadata={
            'user_id': user.id,
            'date': date_value.isoformat(),
            'reminder_type': 'task_digest',
        },
        cancelled=False,
    )
