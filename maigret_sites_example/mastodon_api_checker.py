"""
Mastodon API-backed Maigret checker (example).
Produces the same shape Maigret expects.
"""
import os
from .mastodon_api_resolver import resolve_mastodon_api

DEFAULT_RANK = 120

def check(username, settings=None, logger=None):
    instance_hint = os.getenv("MAIGRET_MASTODON_INSTANCE")
    resolved = resolve_mastodon_api(username, instance_hint=instance_hint)
    if resolved.get("status") == "found":
        short = username.lstrip("@").split("@")[0]
        return {
            "http_status": 200,
            "ids_usernames": {short: "username"},
            "is_similar": False,
            "parsing_enabled": True,
            "rank": DEFAULT_RANK,
            "url": resolved.get("url"),
            "raw": resolved,
        }
    return {
        "http_status": None,
        "ids_usernames": {},
        "is_similar": False,
        "parsing_enabled": False,
        "rank": DEFAULT_RANK,
        "url": None,
        "raw": resolved,
    }
