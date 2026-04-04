"""Generate db_meta.json from data.json for the auto-update system."""

import argparse
import hashlib
import json
import os.path as path
import sys
from datetime import datetime, timezone

RESOURCES_DIR = path.join(path.dirname(path.dirname(path.abspath(__file__))), "maigret", "resources")
DATA_JSON_PATH = path.join(RESOURCES_DIR, "data.json")
META_JSON_PATH = path.join(RESOURCES_DIR, "db_meta.json")
DEFAULT_DATA_URL = "https://raw.githubusercontent.com/soxoj/maigret/main/maigret/resources/data.json"


def get_current_version():
    version_file = path.join(path.dirname(path.dirname(path.abspath(__file__))), "maigret", "__version__.py")
    with open(version_file) as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip("'\"")
    return "0.0.0"


def main():
    parser = argparse.ArgumentParser(description="Generate db_meta.json from data.json")
    parser.add_argument("--min-version", default=None, help="Minimum compatible maigret version (default: current version)")
    parser.add_argument("--data-url", default=DEFAULT_DATA_URL, help="URL where data.json can be downloaded")
    args = parser.parse_args()

    min_version = args.min_version or get_current_version()

    with open(DATA_JSON_PATH, "rb") as f:
        raw = f.read()
        sha256 = hashlib.sha256(raw).hexdigest()

    data = json.loads(raw)
    sites_count = len(data.get("sites", {}))

    meta = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sites_count": sites_count,
        "min_maigret_version": min_version,
        "data_sha256": sha256,
        "data_url": args.data_url,
    }

    with open(META_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=4, ensure_ascii=False)

    print(f"Generated {META_JSON_PATH}")
    print(f"  sites: {sites_count}")
    print(f"  sha256: {sha256[:16]}...")
    print(f"  min_version: {min_version}")


if __name__ == "__main__":
    main()
