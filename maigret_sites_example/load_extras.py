# maigret_sites_example/load_extras.py
"""Load and merge an extras JSON file into a default sites dict.

Usage patterns:
  - default_sites = load_extra_sites(default_sites)        # runtime merge
  - merged = merge_sites(default_sites, extra_path)        # pure function

This file intentionally lives outside `maigret/` to avoid colliding with upstream modules.
"""
from pathlib import Path
import json
import os
from typing import Dict, Any

def read_json_path(path: str) -> Dict[str, Any]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        return json.load(fh)

def merge_sites(default_sites: Dict[str, Any], extra_path: str) -> Dict[str, Any]:
    """
    Return a new dict with keys from extra_path merged in only when they do not exist.
    Non-destructive: does not overwrite existing keys.
    """
    if not extra_path:
        return default_sites
    p = Path(extra_path)
    if not p.exists():
        return default_sites
    try:
        extra = read_json_path(extra_path)
    except Exception:
        # fail safe: return defaults if JSON invalid
        return default_sites

    merged = dict(default_sites)  # shallow copy
    for k, v in extra.items():
        if k not in merged:
            merged[k] = v
    return merged

def load_extra_sites(default_sites: Dict[str, Any],
                     env_var: str = "MAIGRET_EXTRA_SITES",
                     cli_path: str | None = None) -> Dict[str, Any]:
    """
    Merge extras into default_sites. CLI path (explicit) takes precedence over environment var.
    """
    extra_path = cli_path or os.getenv(env_var)
    return merge_sites(default_sites, extra_path)

