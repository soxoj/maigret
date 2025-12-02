"""
Shodan-backed checker (runtime-read API key so tests can monkeypatch).
Opt-in: requires SHODAN_API_KEY env var. Safe/no-op when missing.
"""
import os
import time
from typing import Dict, Any
import requests

SHODAN_BASE = "https://api.shodan.io"

def _get_with_backoff(url, params=None, headers=None, timeout=6, retries=2):
    backoff = 0.5
    for i in range(retries + 1):
        try:
            r = requests.get(url, params=params, headers=headers or {}, timeout=timeout)
            return r
        except requests.RequestException:
            if i == retries:
                raise
            time.sleep(backoff)
            backoff *= 2

def check(username: str, settings=None, logger=None, timeout=6) -> Dict[str, Any]:
    """
    Runtime-checker: reads SHODAN_API_KEY from environment at call-time,
    so tests can monkeypatch the environment reliably.
    """
    api_key = os.environ.get("SHODAN_API_KEY")
    if not api_key:
        if logger:
            logger.debug("shodan_checker: SHODAN_API_KEY not set, skipping API call.")
        return {
            "http_status": None,
            "ids_usernames": {},
            "is_similar": False,
            "parsing_enabled": False,
            "rank": 999,
            "url": None,
        }

    search_url = f"{SHODAN_BASE}/shodan/host/search"
    params = {"key": api_key, "query": username}
    try:
        r = _get_with_backoff(search_url, params=params, timeout=timeout)
    except Exception as e:
        if logger:
            logger.debug("shodan_checker network error: %s", e)
        return {"http_status": None, "ids_usernames": {}, "is_similar": False, "parsing_enabled": True, "rank": 999, "url": search_url}

    try:
        data = r.json()
    except Exception:
        data = {}

    # Conservative parsing: mark as found when total > 0
    ids = {}
    if isinstance(data, dict) and data.get("total", 0) > 0:
        ids = {username: "username"}

    return {
        "http_status": getattr(r, "status_code", None),
        "ids_usernames": ids,
        "is_similar": False,
        "parsing_enabled": True,
        "rank": 120,
        "url": search_url,
        "raw": data,
    }
