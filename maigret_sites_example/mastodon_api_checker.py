"""
Mastodon API-backed Maigret checker (example).

This checker calls the resolver via its module so tests can patch the resolver
function (patching mastodon_api_resolver.resolve_mastodon_api will affect us).
"""
import os
from typing import Any, Dict

# import the resolver module (importing the module object allows tests to patch
# the function on the module, which `from ... import func` would not respect).
from . import mastodon_api_resolver

DEFAULT_RANK = 120

def _empty_result(raw: Any = None) -> Dict:
    return {
        "http_status": None,
        "ids_usernames": {},
        "is_similar": False,
        "parsing_enabled": False,
        "rank": DEFAULT_RANK,
        "url": None,
        "raw": raw,
    }

def _found_result(username: str, url: str, raw: Any = None) -> Dict:
    short = username.lstrip("@").split("@")[0]
    return {
        "http_status": 200,
        "ids_usernames": {short: "username"},
        "is_similar": False,
        "parsing_enabled": True,
        "rank": DEFAULT_RANK,
        "url": url,
        "raw": raw,
    }

def check(username: str, settings=None, logger=None) -> Dict:
    """
    Check a Mastodon account via the API resolver.

    - username: may be "@alice", "alice", or "alice@instance"
    - settings, logger: accepted for compatibility (not used here)
    """
    instance_hint = os.getenv("MAIGRET_MASTODON_INSTANCE")

    # Call the resolver via module so tests can patch it:
    resolved = mastodon_api_resolver.resolve_mastodon_api(username, instance_hint=instance_hint)

    # Defensive handling
    if not isinstance(resolved, dict):
        return _empty_result(raw=resolved)

    status = resolved.get("status")
    if isinstance(status, str) and status.lower() == "found":
        url = resolved.get("url")
        if not url and isinstance(resolved.get("data"), dict):
            url = resolved["data"].get("url")
        return _found_result(username, url, raw=resolved)

    return _empty_result(raw=resolved)
