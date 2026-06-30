from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as datetime_timezone
import os
import re
from typing import Iterable
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import logging
import requests
from bs4 import BeautifulSoup
from django.utils import timezone

logger = logging.getLogger(__name__)


IST = ZoneInfo('Asia/Kolkata')
REQUEST_TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class ContestSnapshot:
    source_slug: str
    source_name: str
    source_key: str
    title: str
    url: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int | None
    status: str
    raw_data: dict


@dataclass(frozen=True)
class ContestSourceSpec:
    slug: str
    name: str
    url: str
    kind: str


SOURCE_SPECS = (
    ContestSourceSpec(slug='codeforces', name='Codeforces', url='https://codeforces.com/api/contest.list?gym=false', kind='json'),
    ContestSourceSpec(slug='leetcode', name='LeetCode', url='https://leetcode.com/contest/', kind='html'),
    ContestSourceSpec(slug='geeksforgeeks', name='GeeksforGeeks', url='https://www.geeksforgeeks.org/events/', kind='html'),
    ContestSourceSpec(slug='codechef', name='CodeChef', url='https://www.codechef.com/api/list/contests/all?type=upcoming', kind='json'),
    ContestSourceSpec(slug='portes', name='Portes', url=os.environ.get('PORTES_CONTESTS_URL', '').strip(), kind='html'),
)


def _request(url: str) -> requests.Response:
    response = requests.get(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) StreakMaintainer/1.0',
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response


def _status_from_time(start_time: datetime, end_time: datetime) -> str:
    now = timezone.now().astimezone(IST)
    if start_time <= now <= end_time:
        return 'live'
    if now > end_time:
        return 'ended'
    return 'upcoming'


def _parse_ist_timestamp(text: str, pattern: str) -> datetime | None:
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None

    date_text = match.group(1).strip()
    for date_format in ('%a, %b %d, %H:%M', '%B %d, %Y %I:%M %p', '%b %d, %Y %I:%M %p'):
        try:
            parsed = datetime.strptime(date_text, date_format)
            return parsed.replace(tzinfo=IST)
        except ValueError:
            continue

    return None


def fetch_codeforces_contests() -> list[ContestSnapshot]:
    response = _request('https://codeforces.com/api/contest.list?gym=false')
    payload = response.json()
    contests = []

    for contest in payload.get('result', []):
        contest_id = str(contest.get('id', '')).strip()
        name = str(contest.get('name', '')).strip()
        start_seconds = contest.get('startTimeSeconds')
        duration_seconds = contest.get('durationSeconds') or 0

        if not contest_id or not name or not start_seconds:
            continue

        start_time = datetime.fromtimestamp(start_seconds, tz=datetime_timezone.utc).astimezone(IST)
        duration_minutes = int(duration_seconds // 60) if duration_seconds else None
        end_time = start_time + timedelta(seconds=duration_seconds) if duration_seconds else start_time
        phase = str(contest.get('phase', '')).upper()
        if phase == 'BEFORE':
            status = 'upcoming'
        elif phase in {'CODING', 'PENDING_SYSTEM_TEST', 'SYSTEM_TEST'}:
            status = 'live'
        elif phase == 'FINISHED':
            status = 'ended'
        else:
            status = _status_from_time(start_time, end_time)

        contests.append(
            ContestSnapshot(
                source_slug='codeforces',
                source_name='Codeforces',
                source_key=contest_id,
                title=name,
                url=f'https://codeforces.com/contests/{contest_id}',
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration_minutes,
                status=status,
                raw_data=contest,
            ),
        )

    return contests


def _clean_title(title: str) -> str:
    return re.sub(r'\s+', ' ', title).strip(' -|')


def _extract_contest_cards(html: str, base_url: str, source_slug: str, source_name: str, duration_minutes: int | None = None) -> list[ContestSnapshot]:
    soup = BeautifulSoup(html, 'html.parser')
    contest_cards: list[ContestSnapshot] = []
    seen_keys: set[str] = set()

    for anchor in soup.find_all('a', href=True):
        href = anchor['href']
        if '/contest/' not in href and '/event/' not in href:
            continue

        absolute_url = urljoin(base_url, href)
        path = urlparse(absolute_url).path.rstrip('/')
        source_key = path.split('/')[-1]
        if not source_key or source_key in seen_keys:
            continue

        container = anchor.find_parent(['article', 'section', 'div', 'li']) or anchor.parent
        container_text = ' '.join(container.stripped_strings) if container else anchor.get_text(' ', strip=True)
        title = _clean_title(anchor.get_text(' ', strip=True)) or source_key.replace('-', ' ').title()

        start_time = None
        if source_slug == 'leetcode':
            start_time = _parse_ist_timestamp(container_text, r'((?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s+[A-Z][a-z]{2}\s+\d{1,2},\s+\d{1,2}:\d{2})\s+GMT\+05:30')
        elif source_slug in {'geeksforgeeks', 'portes'}:
            start_time = _parse_ist_timestamp(container_text, r'((?:[A-Z][a-z]+\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}\s+[AP]M)\s+IST)')

        if not start_time:
            continue

        end_time = start_time + timedelta(minutes=duration_minutes or 90)
        status = _status_from_time(start_time, end_time)
        contest_cards.append(
            ContestSnapshot(
                source_slug=source_slug,
                source_name=source_name,
                source_key=source_key,
                title=title,
                url=absolute_url,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration_minutes,
                status=status,
                raw_data={'title': title, 'container_text': container_text, 'url': absolute_url},
            ),
        )
        seen_keys.add(source_key)

    return contest_cards


def fetch_leetcode_contests() -> list[ContestSnapshot]:
    url = 'https://leetcode.com/graphql/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Content-Type': 'application/json',
        'Referer': 'https://leetcode.com/contest/',
    }
    payload = {
        'query': 'query topTwoContests { topTwoContests { title titleSlug startTime duration } }',
        'operationName': 'topTwoContests'
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    
    contests = []
    top_two = data.get('data', {}).get('topTwoContests', []) or []
    for c in top_two:
        title = c.get('title')
        slug = c.get('titleSlug')
        start_seconds = c.get('startTime')
        duration_seconds = c.get('duration') or 5400  # Default 90 min
        
        if not title or not slug or not start_seconds:
            continue
            
        start_time = datetime.fromtimestamp(start_seconds, tz=datetime_timezone.utc).astimezone(IST)
        duration_minutes = int(duration_seconds // 60)
        end_time = start_time + timedelta(seconds=duration_seconds)
        status = _status_from_time(start_time, end_time)
        
        contests.append(
            ContestSnapshot(
                source_slug='leetcode',
                source_name='LeetCode',
                source_key=slug,
                title=title,
                url=f'https://leetcode.com/contest/{slug}',
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration_minutes,
                status=status,
                raw_data=c,
            )
        )
        
    return contests


def fetch_geeksforgeeks_contests() -> list[ContestSnapshot]:
    html = _request('https://www.geeksforgeeks.org/events/').text
    return _extract_contest_cards(html, 'https://www.geeksforgeeks.org/events/', 'geeksforgeeks', 'GeeksforGeeks')


def fetch_portes_contests() -> list[ContestSnapshot]:
    feed_url = os.environ.get('PORTES_CONTESTS_URL', '').strip()
    if not feed_url:
        return []

    html = _request(feed_url).text
    return _extract_contest_cards(html, feed_url, 'portes', 'Portes')


def fetch_codechef_contests() -> list[ContestSnapshot]:
    try:
        response = _request('https://www.codechef.com/api/list/contests/all?type=upcoming')
        payload = response.json()
    except Exception:
        return []

    contests = []
    # Both future_contests and present_contests are relevant
    raw_list = payload.get('future_contests', []) + payload.get('present_contests', [])
    for c in raw_list:
        code = str(c.get('contest_code', '')).strip()
        name = str(c.get('contest_name', '')).strip()
        start_str = c.get('contest_start_date')
        end_str = c.get('contest_end_date')
        duration_minutes = c.get('contest_duration')

        if not code or not name or not start_str:
            continue

        try:
            start_time = datetime.strptime(start_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=IST)
            end_time = datetime.strptime(end_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=IST)
        except ValueError:
            try:
                start_time = datetime.strptime(start_str, '%d %b %Y %H:%M:%S').replace(tzinfo=IST)
                end_time = datetime.strptime(end_str, '%d %b %Y %H:%M:%S').replace(tzinfo=IST)
            except ValueError:
                continue

        try:
            dur = int(float(duration_minutes))
        except (ValueError, TypeError):
            dur = int((end_time - start_time).total_seconds() // 60)

        status = _status_from_time(start_time, end_time)
        contests.append(
            ContestSnapshot(
                source_slug='codechef',
                source_name='CodeChef',
                source_key=code,
                title=name,
                url=f'https://www.codechef.com/{code}',
                start_time=start_time,
                end_time=end_time,
                duration_minutes=dur,
                status=status,
                raw_data=c,
            )
        )
    return contests


def fetch_contests_for_source(source_slug: str) -> list[ContestSnapshot]:
    if source_slug == 'codeforces':
        return fetch_codeforces_contests()
    if source_slug == 'leetcode':
        return fetch_leetcode_contests()
    if source_slug == 'geeksforgeeks':
        return fetch_geeksforgeeks_contests()
    if source_slug == 'codechef':
        return fetch_codechef_contests()
    if source_slug == 'portes':
        return fetch_portes_contests()
    return []


def fetch_all_contests() -> list[ContestSnapshot]:
    contest_snapshots: list[ContestSnapshot] = []
    for source_spec in SOURCE_SPECS:
        try:
            contest_snapshots.extend(fetch_contests_for_source(source_spec.slug))
        except Exception as e:
            logger.error(f"Error fetching contests from source '{source_spec.slug}': {e}")
            continue

    contest_snapshots.sort(key=lambda contest: (contest.start_time, contest.source_slug, contest.title))
    return contest_snapshots


def active_source_slugs() -> Iterable[str]:
    for source_spec in SOURCE_SPECS:
        if source_spec.slug == 'portes' and not source_spec.url:
            continue
        yield source_spec.slug
