#!/usr/bin/env python3
"""
Probe likely false-positive sites among the top-N Alexa-ranked entries.

For each of K random *distinct* usernames taken from ``usernameClaimed`` fields in
the Maigret database, runs a clean ``maigret`` scan (``--top-sites N --json simple|ndjson``).
Sites that return CLAIMED in *every* run are reported: unrelated random claimed
handles are unlikely to all exist on the same third-party site, so such sites are
candidates for broken checks.
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_username_claimed_pool(db_path: Path) -> list[str]:
    with db_path.open(encoding="utf-8") as f:
        data = json.load(f)
    sites = data.get("sites") or {}
    seen: set[str] = set()
    pool: list[str] = []
    for _name, site in sites.items():
        u = (site or {}).get("usernameClaimed")
        if not u or not isinstance(u, str):
            continue
        u = u.strip()
        if not u or u in seen:
            continue
        seen.add(u)
        pool.append(u)
    return pool


def run_maigret(
    *,
    username: str,
    db_path: Path,
    out_dir: Path,
    top_sites: int,
    json_format: str,
    quiet: bool,
) -> Path:
    """Run maigret subprocess; return path to the written JSON report."""
    safe = username.replace("/", "_")
    report_name = f"report_{safe}_{json_format}.json"
    report_path = out_dir / report_name

    cmd = [
        sys.executable,
        "-m",
        "maigret",
        username,
        "--db",
        str(db_path),
        "--top-sites",
        str(top_sites),
        "--json",
        json_format,
        "--folderoutput",
        str(out_dir),
        "--no-progressbar",
        "--no-color",
        "--no-recursion",
        "--no-extracting",
    ]
    sink = subprocess.DEVNULL if quiet else None
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root()),
        text=True,
        stdout=sink,
        stderr=sink,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"maigret exited with {proc.returncode} for username {username!r}"
        )
    if not report_path.is_file():
        raise FileNotFoundError(f"Expected report missing: {report_path}")
    return report_path


def claimed_sites_from_report(path: Path, json_format: str) -> set[str]:
    if json_format == "simple":
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return set()
        return set(data.keys())
    # ndjson: one object per line, each has "sitename"
    sites: set[str] = set()
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            name = obj.get("sitename")
            if isinstance(name, str) and name:
                sites.add(name)
    return sites


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Pick random distinct usernameClaimed values, run maigret --top-sites N "
            "with JSON reports, and list sites that claimed all of them (suspicious FP)."
        )
    )
    parser.add_argument(
        "--db",
        "-b",
        type=Path,
        default=repo_root() / "maigret" / "resources" / "data.json",
        help="Path to Maigret data.json (a temp copy is used for runs).",
    )
    parser.add_argument(
        "--top-sites",
        "-n",
        type=int,
        default=500,
        metavar="N",
        help="Value for maigret --top-sites (default: 500).",
    )
    parser.add_argument(
        "--samples",
        "-k",
        type=int,
        default=5,
        metavar="K",
        help="How many distinct random usernames to draw (default: 5).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="RNG seed for reproducible username selection.",
    )
    parser.add_argument(
        "--json",
        dest="json_format",
        default="simple",
        choices=["simple", "ndjson"],
        help="JSON report type passed to maigret -J (default: simple).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Print maigret stdout/stderr (default: suppress child output).",
    )
    args = parser.parse_args()
    quiet = not args.verbose

    db_src = args.db.resolve()
    if not db_src.is_file():
        print(f"Database not found: {db_src}", file=sys.stderr)
        return 2

    pool = load_username_claimed_pool(db_src)
    if len(pool) < args.samples:
        print(
            f"Need at least {args.samples} distinct usernameClaimed entries, "
            f"found {len(pool)}.",
            file=sys.stderr,
        )
        return 2

    rng = random.Random(args.seed)
    picked = rng.sample(pool, args.samples)

    print(f"Database: {db_src}")
    print(f"--top-sites {args.top_sites}, {args.samples} random usernameClaimed:")
    for i, u in enumerate(picked, 1):
        print(f"  {i}. {u}")

    site_sets: list[set[str]] = []
    with tempfile.TemporaryDirectory(prefix="maigret_fp_probe_") as tmp:
        tmp_path = Path(tmp)
        db_work = tmp_path / "data.json"
        shutil.copyfile(db_src, db_work)

        for u in picked:
            print(f"\nRunning maigret for {u!r} ...", flush=True)
            report = run_maigret(
                username=u,
                db_path=db_work,
                out_dir=tmp_path,
                top_sites=args.top_sites,
                json_format=args.json_format,
                quiet=quiet,
            )
            sites = claimed_sites_from_report(report, args.json_format)
            site_sets.append(sites)
            print(f"  -> {len(sites)} positive site(s) in JSON", flush=True)

    always = set.intersection(*site_sets) if site_sets else set()
    print("\n--- Sites with CLAIMED in all runs (candidates for false positives) ---")
    if not always:
        print("(none)")
    else:
        for name in sorted(always):
            print(name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
