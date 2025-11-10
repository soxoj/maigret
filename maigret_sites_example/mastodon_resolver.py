# maigret_sites_example/mastodon_resolver.py
import requests

COMMON_INSTANCES = ["mastodon.social", "fosstodon.org", "mstdn.social", "chaos.social"]

def resolve_mastodon(nickname, instance_hint=None, timeout=6):
    candidates = []
    if "@" in nickname:
        # accept nickname@instance
        user, inst = nickname.lstrip("@").split("@",1)
        candidates.append((user, inst))
    elif instance_hint:
        candidates.append((nickname, instance_hint))
    else:
        for inst in COMMON_INSTANCES:
            candidates.append((nickname, inst))

    for user, inst in candidates:
        url = f"https://{inst}/@{user}"
        try:
            r = requests.get(url, timeout=timeout, headers={"User-Agent":"maigret/extended"})
            if r.status_code == 200:
                return {"status":"found","url":url}
            if r.status_code == 404:
                continue
        except Exception:
            continue
    return {"status":"not_found"}

