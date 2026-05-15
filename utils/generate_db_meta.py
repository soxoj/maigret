"""Generate db_meta.json from data.json for the auto-update system."""

import argparse
import hashlib
import json
import os.path as path
from datetime import datetime, timezone
from typing import Optional, Tuple

RESOURCES_DIR = path.join(path.dirname(path.dirname(path.abspath(__file__))), "maigret", "resources")
DATA_JSON_PATH = path.join(RESOURCES_DIR, "data.json")
META_JSON_PATH = path.join(RESOURCES_DIR, "db_meta.json")
DEFAULT_DATA_URL = "https://raw.githubusercontent.com/soxoj/maigret/main/maigret/resources/data.json"

_TIMESTAMP_KEY = "updated_at"


def get_current_version():
    version_file = path.join(path.dirname(path.dirname(path.abspath(__file__))), "maigret", "__version__.py")
    with open(version_file) as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip("'\"")
    return "0.0.0"


def build_meta(data_path: str, min_version: str, data_url: str, now: Optional[datetime] = None) -> dict:
    """Build a db_meta dict for the given data.json. Does not touch the filesystem."""
    with open(data_path, "rb") as f:
        raw = f.read()
    data = json.loads(raw)
    ts = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "version": 1,
        _TIMESTAMP_KEY: ts,
        "sites_count": len(data.get("sites", {})),
        "min_maigret_version": min_version,
        "data_sha256": hashlib.sha256(raw).hexdigest(),
        "data_url": data_url,
    }


def meta_payload_equals(a: dict, b: dict) -> bool:
    """Compare two db_meta dicts ignoring the volatile 'updated_at' field."""
    a_clean = {k: v for k, v in a.items() if k != _TIMESTAMP_KEY}
    b_clean = {k: v for k, v in b.items() if k != _TIMESTAMP_KEY}
    return a_clean == b_clean


def _read_meta(meta_path: str) -> Optional[dict]:
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def write_meta_if_changed(
    data_path: str,
    meta_path: str,
    min_version: str,
    data_url: str,
    now: Optional[datetime] = None,
) -> Tuple[dict, bool]:
    """Generate db_meta.json next to data.json. Skip the write entirely if
    the only thing that would change is `updated_at` — keeps the file (and
    git/precommit hooks) quiet when the underlying site database hasn't
    actually moved.

    Returns the meta dict that *would* be written and a bool indicating
    whether a write happened.
    """
    new_meta = build_meta(data_path, min_version, data_url, now=now)
    existing = _read_meta(meta_path)
    if existing is not None and meta_payload_equals(existing, new_meta):
        return existing, False

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(new_meta, f, indent=4, ensure_ascii=False)
    return new_meta, True


def main():
    parser = argparse.ArgumentParser(description="Generate db_meta.json from data.json")
    parser.add_argument("--min-version", default=None, help="Minimum compatible maigret version (default: current version)")
    parser.add_argument("--data-url", default=DEFAULT_DATA_URL, help="URL where data.json can be downloaded")
    args = parser.parse_args()

    min_version = args.min_version or get_current_version()
    meta, written = write_meta_if_changed(DATA_JSON_PATH, META_JSON_PATH, min_version, args.data_url)

    if written:
        print(f"Generated {META_JSON_PATH}")
    else:
        print(f"Skipped {META_JSON_PATH}: nothing changed except timestamp")
    print(f"  sites: {meta['sites_count']}")
    print(f"  sha256: {meta['data_sha256'][:16]}...")
    print(f"  min_version: {meta['min_maigret_version']}")


if __name__ == "__main__":
    main()
