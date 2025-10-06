"""
Dev shim for socid_extractor used by tests.

Provides:
 - __version__
 - extract(text) -> dict-like mapping {id: type}
 - mutate_url(url) -> iterable of (url, headers)
 - parse(url, cookies_str='', headers=None, timeout=5) -> (page_text, meta_dict)

This shim intentionally avoids network I/O and returns deterministic results for tests.
"""
__version__ = "0.0.0"

import re
from typing import Iterable, Tuple, Dict, Any

def extract(text: str) -> Dict[str, str]:
    """
    Return a mapping of extracted ids -> id_type.
    For test determinism: if the text contains '/user/<name>' or 'reddit.com/user/<name>'
    then return {'<name>':'username'}. Otherwise return empty dict.
    """
    if not text:
        return {}
    # look for reddit-style user paths
    m = re.search(r'(?:reddit\.com/)?/?user/([A-Za-z0-9_-]+)', text)
    if m:
        name = m.group(1)
        return {name: "username"}
    return {}

def mutate_url(url: str) -> Iterable[Tuple[str, set]]:
    """
    Return additional url/header tuples. Keep empty by default.
    """
    return []

def parse(url: str, cookies_str: str = "", headers=None, timeout: int = 5) -> Tuple[str, Dict[str, Any]]:
    """
    Minimal parse implementation:
      - If url contains '/user/<name>' return a small page text that extract() can parse.
      - Otherwise return empty page.
    Return: (page_text, meta_dict)
    """
    # If it's a reddit user URL, produce HTML snippet including the username.
    m = re.search(r'/user/([A-Za-z0-9_-]+)', url or "")
    if m:
        user = m.group(1)
        page = f"<html><body>Profile page for {user} - /user/{user}</body></html>"
        meta = {"url": url}
        return (page, meta)
    return ("", {"url": url})
