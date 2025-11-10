# maigret_sites_example/tiktok_checker.py
import re
import requests
from time import sleep

# small helper for retries + backoff
def http_get_with_backoff(url, headers=None, timeout=10, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            return r
        except Exception:
            sleep(1 + i*0.5)
    raise

def check_tiktok(nickname, user_agent=None):
    ua = user_agent or "maigret/extended (+https://github.com/dmoney96/maigretexpanded)"
    headers = {"User-Agent": ua, "Accept": "text/html,application/json"}
    urls = [
        f"https://www.tiktok.com/@{nickname}",
        f"https://m.tiktok.com/v/{nickname}",
        f"https://vm.tiktok.com/{nickname}/"
    ]
    for u in urls:
        try:
            r = http_get_with_backoff(u, headers=headers, timeout=8)
        except Exception as e:
            return {"status": "error", "error": str(e)}
        # direct 404 => not found
        if r.status_code == 404:
            continue
        # JSON response guard
        ct = r.headers.get("Content-Type", "")
        text = r.text or ""
        # Heuristic: page contains JSON with "user" or "uniqueId"
        if "uniqueId" in text or re.search(r'"userId"\s*:', text) or "class=\"share-title\"" in text:
            return {"status": "found", "url": u}
        # Heuristic negative
        if "This account is private" in text or "Not Found" in text or r.status_code in (403, 429):
            # 403/429 might be rate-limited or blocked — treat as unknown
            if r.status_code in (403,429):
                return {"status": "unknown", "url": u, "code": r.status_code}
            continue
    return {"status": "not_found"}

