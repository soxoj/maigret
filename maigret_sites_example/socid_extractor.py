"""
DEV SHIM (maigretexpanded)
This file is a local development shim to let the test-suite run without
pulling the real `socid_extractor` dependency. It should be replaced
with the real package or removed before upstreaming if upstream prefers
the real dependency.

It intentionally implements minimal functions expected by the tests:
 - extract(text) -> dict-like mapping of site identifiers (or [] if none)
 - parse(url, ...) -> simplified parser stub used in tests (if needed)
 - mutate_url(url) -> yields additional (url, headers) tuples
 - __version__ string for CLI metadata.
"""

__version__ = "0.0.0-dev-maigretexpanded"

def extract(text):
    # return empty dict by default (adapt shape if Maigret expects different)
    return {}

def parse(url, cookies_str='', headers=None, timeout=5):
    # Minimal parse stub: return (page_text, http_meta)
    # Tests that require full parsing should mock the parser anyway.
    return ("", {})

def mutate_url(url):
    # yield no extra URLs by default
    return []
