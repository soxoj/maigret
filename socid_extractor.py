"""
Temporary dev shim for `socid_extractor` so tests can import the expected symbols.

This provides a very small, safe API surface:
 - __version__ (string)
 - extract(text) -> list
 - mutate_url(url) -> iterable of (url, headers)
 - parse(url, cookies_str='', headers=None, timeout=5) -> (page_text, meta_dict)

Replace this shim with the real package before upstreaming.
"""
__version__ = "0.0.0"

def extract(text):
    # Minimal safe implementation: return empty list of extracted ids/entities.
    return []

def mutate_url(url):
    # Return additional (url, headers) candidates if needed.
    # Keep empty by default so Maigret falls back to the original URL only.
    return []

def parse(url, cookies_str="", headers=None, timeout=5):
    """
    Minimal parse() compatible with Maigret usage.
    Maigret expects (page_text, meta) where meta can be dict-like.
    We return a safe empty page and an empty meta dict.
    """
    # Keep deterministic, avoid network calls in tests.
    return ("", {})
