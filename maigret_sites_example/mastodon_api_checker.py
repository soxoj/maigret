# maigret_sites_example/mastodon_api_checker.py
"""
Mastodon API-style checker (example).

This checker calls the resolver via the module (mastodon_resolver.resolve_mastodon)
so tests that patch the resolver at the module path will apply correctly.

It only reports a hit when the resolver returns {"status": "found"}.
"""
from typing import Dict, Any
import os

# import the module object (so tests can patch mastodon_resolver.resolve_mastodon)
from . import mastodon_resolver

DEFAULT_RANK = 120


def check(username: str, settings=None, logger=None, timeout: int = 6) -> Dict[str, Any]:
    """
    Maigret-style checker for Mastodon-like handles.

    Args:
      username: input username (may be '@name', 'name@instance', or 'name')
      settings, logger: optional compatibility parameters (not used here)
      timeout: how long to wait for HTTP probes in the resolver

    Returns:
      dict with keys: http_status, ids_usernames, parsing_enabled, is_similar,
                      rank, url, raw
    """
    queried = username
    stripped = queried.lstrip("@")
    canon = stripped.split("@", 1)[0]

    instance_hint = os.getenv("MAIGRET_MASTODON_INSTANCE")

    try:
        resolved = mastodon_resolver.resolve_mastodon(queried, instance_hint=instance_hint, timeout=timeout)
    except Exception as exc:
        if logger:
            try:
                logger.debug("mastodon_resolver exception: %s", exc)
            except Exception:
                pass
        resolved = {"status": "not_found"}

    result: Dict[str, Any] = {
        "http_status": None,
        "ids_usernames": {},
        "is_similar": False,
        # default for not-found case
        "parsing_enabled": False,
        "rank": DEFAULT_RANK,
        "url": None,
        "raw": resolved,
    }

    if resolved.get("status") == "found":
        result.update(
            {
                "http_status": 200,
                "ids_usernames": {canon: "username"},
                "is_similar": False,
                # For a found account we enable parsing (test expects True)
                "parsing_enabled": True,
                "rank": DEFAULT_RANK,
                "url": resolved.get("url"),
                "raw": resolved,
            }
        )

    return result
