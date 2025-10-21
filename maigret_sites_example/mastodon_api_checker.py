"""
Mastodon API-style checker (example).

Uses the helper resolve_mastodon_api() (in mastodon_api_resolver.py)
which probes instances using the Mastodon accounts lookup endpoint.
This checker reports a hit when the resolver returns {"status": "found"}.
"""
from typing import Dict, Any, Optional
import os

# import the resolver module (not the function) so tests that patch the
# function on the module will affect calls performed here.
from . import mastodon_api_resolver as resolver

DEFAULT_RANK = 120


def check(username: str, settings: Optional[object] = None, logger: Optional[object] = None, timeout: int = 6) -> Dict[str, Any]:
    """
    Maigret-style checker for Mastodon-like handles.

    Args:
        username: input username (may be '@name', 'name@instance' or 'name')
        settings, logger: optional compatibility parameters (not used here)
        timeout: passed to resolver

    Returns:
        dict with keys at least: http_status, ids_usernames, parsing_enabled, rank, url, raw
    """
    queried = username or ""
    queried_stripped = queried.lstrip("@")

    # allow overriding the instance to probe via env var
    instance_hint = os.getenv("MAIGRET_MASTODON_INSTANCE")

    try:
        # call the resolver through the module so test patching works:
        resolved = resolver.resolve_mastodon_api(queried, instance_hint=instance_hint, timeout=timeout)
    except Exception as exc:
        # Do not raise during checks — treat as not found; log if logger is present
        if logger:
            try:
                logger.debug("mastodon resolver exception: %s", exc)
            except Exception:
                pass
        resolved = {"status": "not_found"}

    # Default not-found result
    result: Dict[str, Any] = {
        "http_status": None,
        "ids_usernames": {},
        "is_similar": False,
        "parsing_enabled": False,
        "rank": DEFAULT_RANK,
        "url": None,
        "raw": resolved,
    }

    if resolved.get("status") == "found":
        # Extract canonical username (drop leading '@' and any instance part)
        canon = queried_stripped.split("@", 1)[0]
        result.update(
            {
                "http_status": 200,
                "ids_usernames": {canon: "username"},
                "is_similar": False,
                # this checker provides a found profile URL / data so parsing_enabled = True
                "parsing_enabled": True,
                "rank": DEFAULT_RANK,
                "url": resolved.get("url"),
                "raw": resolved,
            }
        )

    return result
