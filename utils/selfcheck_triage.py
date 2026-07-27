#!/usr/bin/env python3
"""
Triage report for `maigret --self-check --diagnose` output.

False negatives (claimed user not detected) and check errors are invisible
in normal usage: users just don't see the account. This tool surfaces them.

Workflow:

    # 1. Run self-check on a TEMP COPY of the DB (scans/self-check may rewrite it)
    cp maigret/resources/data.json /tmp/data.json
    echo n | python3 -m maigret --self-check --diagnose --top-sites 500 \
        --db /tmp/data.json --no-progressbar --no-color > /tmp/selfcheck.log 2>&1

    # 2. Classify and rank failures by site popularity
    python3 utils/selfcheck_triage.py /tmp/selfcheck.log /tmp/data.json
"""

import argparse
import json
import re
from pathlib import Path


KINDS = ("FALSE_NEGATIVE", "ERROR", "CONNECT_FAIL", "FALSE_POSITIVE", "OTHER")


def parse_diagnosis_blocks(log_text: str) -> dict:
    """Extract {site_name: [issue, ...]} from --diagnose output."""
    blocks = {}
    cur = None
    for line in log_text.splitlines():
        m = re.match(r"^--- (.+) DIAGNOSIS ---$", line.strip())
        if m:
            cur = m.group(1)
            blocks[cur] = []
            continue
        if cur is None:
            continue
        s = line.strip()
        if s.startswith("- "):
            blocks[cur].append(s[2:])
        elif s.startswith(("Check type:", "Issues:", "Recommendations:", "->")):
            continue
        elif s and not line.startswith("  "):
            cur = None
    return blocks


def classify(issues: list) -> set:
    kinds = set()
    for i in issues:
        if re.search(r"Claimed user .* not detected as claimed", i):
            kinds.add("FALSE_NEGATIVE")
        elif re.search(r"Unclaimed user .* detected as claimed", i):
            kinds.add("FALSE_POSITIVE")
        elif i.startswith("Error checking"):
            kinds.add("ERROR")
        elif "Cannot connect to host" in i:
            kinds.add("CONNECT_FAIL")
        else:
            kinds.add("OTHER")
    return kinds


def main():
    parser = argparse.ArgumentParser(
        description="Classify and rank maigret --self-check --diagnose failures."
    )
    parser.add_argument("log", type=Path, help="Captured self-check output")
    parser.add_argument(
        "db",
        type=Path,
        nargs="?",
        default=Path(__file__).parent.parent / "maigret" / "resources" / "data.json",
        help="data.json used for the run (for alexaRank ordering)",
    )
    parser.add_argument(
        "--kind",
        choices=KINDS,
        help="Show only one failure kind",
    )
    parser.add_argument(
        "--limit", type=int, default=40, help="Max sites per kind (default: 40)"
    )
    args = parser.parse_args()

    sites_cfg = json.loads(args.db.read_text())["sites"]
    blocks = parse_diagnosis_blocks(args.log.read_text(errors="replace"))

    rows = []
    for name, issues in blocks.items():
        cfg = sites_cfg.get(name, {})
        rows.append(
            (
                cfg.get("alexaRank", 9999999),
                name,
                classify(issues),
                issues,
                cfg.get("checkType"),
            )
        )
    rows.sort()

    counts = {}
    for _, _, kinds, _, _ in rows:
        for k in kinds:
            counts[k] = counts.get(k, 0) + 1
    print(f"Total failing sites: {len(rows)}; kinds: {counts}\n")

    shown_kinds = (args.kind,) if args.kind else KINDS
    for label in shown_kinds:
        subset = [r for r in rows if label in r[2]]
        print(f"=== {label} ({len(subset)}) ===")
        for rank, name, kinds, issues, ctype in subset[: args.limit]:
            extra = "+".join(sorted(kinds - {label}))
            extra = f" [{extra}]" if extra else ""
            print(f"  rank={rank:<8} {name} (checkType={ctype}){extra}")
            for i in issues:
                print(f"      * {i[:160]}")
        if len(subset) > args.limit:
            print(f"  ... and {len(subset) - args.limit} more")
        print()


if __name__ == "__main__":
    main()
