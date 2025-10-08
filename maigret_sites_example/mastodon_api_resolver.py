"""Resolve a Mastodon account using instance REST API (acct lookup).
This tries an explicit instance if provided, otherwise probes a short list
of common instances. It does not require a token (public lookup).
"""
from typing import Optional, Dict
import requests

COMMON_INSTANCES = [
    "mastodon.social",
    "fosstodon.org",
    "mstdn.social",
    "chaos.social",
    "mastodon.cloud",
]

DEFAULT_TIMEOUT = 6
USER_AGENT = "maigret-extended/1.0 (+https://github.com/yourname/maigretexpanded)"

def lookup_on_instance(nickname: str, instance: str, timeout: int = DEFAULT_TIMEOUT) -> Dict:
    acct = nickname.lstrip("@").split("@")[0]
    url = f"https://{instance}/api/v1/accounts/lookup"
    params = {"acct": acct}
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get(url, params=params, timeout=timeout, headers=headers)
        if r.status_code == 200:
            try:
                j = r.json()
            except Exception:
                return {"status": "not_found"}
            profile_url = j.get("url") or f"https://{instance}/@{acct}"
            return {"status": "found", "url": profile_url, "data": j}
        elif r.status_code in (404, 410):
            return {"status": "not_found"}
        else:
            return {"status": "not_found", "raw_status": r.status_code}
    except requests.RequestException:
        return {"status": "not_found"}

def resolve_mastodon_api(nickname: str, instance_hint: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT) -> Dict:
    candidates = []
    if "@" in nickname and nickname.lstrip("@").count("@") == 1 and nickname.lstrip("@").split("@",1)[1]:
        user, inst = nickname.lstrip("@").split("@",1)
        candidates.append((user, inst))
    elif instance_hint:
        candidates.append((nickname.lstrip("@"), instance_hint))
    else:
        for inst in COMMON_INSTANCES:
            candidates.append((nickname.lstrip("@"), inst))

    for user, inst in candidates:
        resp = lookup_on_instance(user, inst, timeout=timeout)
        if resp.get("status") == "found":
            return resp
    return {"status": "not_found"}
