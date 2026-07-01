"""
hiring_tracker/scrapers/http_utils.py

One shared requests.Session for every scraper so we get consistent
headers, retry behaviour, and rate limiting in one place instead of
re-implementing it 11 times with 11 slightly different bugs.
"""

import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("hiring_tracker.scrapers")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    retry = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_session = build_session()


def get(url: str, *, delay: float = 1.5, timeout: int = 15, **kwargs) -> requests.Response:
    """GET with a built-in courtesy delay before the request fires."""
    time.sleep(delay)
    resp = _session.get(url, timeout=timeout, **kwargs)
    resp.raise_for_status()
    return resp
