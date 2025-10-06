"""
Simple Mastodon API-backed checker (example).
This is an example pattern to add API-style checkers. It uses the mastodon_resolver
that probes common instances by requesting https://<instance>/@<user>.
A fuller API implementation can call Mastodon instances' REST API when credentials exist.
"""

import os
from .mastodon_resolver import resolve_mastodon

DEFAULT_RANK = 120

def check(username, settings=None, logger=None):
    """
    Return a Maigret-style result dictionary.
    - username: target username (may start with @ or username@instance)
    - settings, logger: optional for compatibility with tests
    """
    instance_hint = os.getenv("MAIGRET_MASTODON_INSTANCE")
    resolved = resolve_mastodon(username, instance_hint=instance_hint, timeout=6)
    if resolved.get("status") == "found":
        return {
            "http_status": 200,
            "ids_usernames": {username.lstrip("@").split("@")[0]: "username"},
            "is_similar": False,
            "parsing_enabled": True,
            "rank": DEFAULT_RANK,
            "url": resolved.get("url"),
            "raw": resolved
        }
    return {
        "http_status": None,
        "ids_usernames": {},
        "is_similar": False,
        "parsing_enabled": False,
        "rank": DEFAULT_RANK,
        "url": None,
        "raw": resolved
    }
