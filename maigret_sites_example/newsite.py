"""
Example site checker for 'NewSite'.
Must expose a `check(username, settings=None, logger=None)` function returning a dict with
keys used by Maigret (http_status, ids_usernames, is_similar, parsing_enabled, rank, url, ...)
Keep it minimal and deterministic for tests.
"""
import requests

def check(username, settings=None, logger=None, timeout=6):
    """Return a result dict for the given username."""
    url = f"https://newsite.com/{username}"
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "maigretexpanded/0.1"})
    except Exception as e:
        # network error — report as not found so tests remain deterministic if mocked
        if logger:
            logger.debug(f"network error while checking {url}: {e}")
        return {"http_status": None, "ids_usernames": {}, "is_similar": False, "parsing_enabled": True, "rank": 999, "url": url}

    found = (r.status_code == 200)
    ids = {username: "username"} if found else {}
    return {
        "http_status": r.status_code,
        "ids_usernames": ids,
        "is_similar": False,
        "parsing_enabled": True,
        "rank": 100,
        "url": url,
    }
