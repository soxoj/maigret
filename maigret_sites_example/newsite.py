"""
Simple example checker for NewSite.
Implements check(username, settings=None, logger=None, timeout=6) -> dict
Keep network calls mocked in tests — this file uses requests normally.
"""
import requests

def check(username, settings=None, logger=None, timeout=6):
    url = f"https://newsite.com/{username}"
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent":"maigretexpanded/0.1"})
    except Exception as e:
        if logger:
            logger.debug("newsite network error: %s", e)
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
