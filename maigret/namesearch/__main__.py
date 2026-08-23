# coding: utf8
"""CLI for the name-search proof of concept."""

import argparse
import asyncio
import json
import logging
import sys
from typing import List, Optional

from .pipeline import plan_search, render_report, run_name_search
from .searchapi import SearchAPIError, get_api_key


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m maigret.namesearch",
        description="OSINT lookup of a person by full name via SearchAPI (proof of concept)",
    )
    parser.add_argument("name", help='full name, e.g. "Dmitrii Danilov"')
    parser.add_argument(
        "--context",
        nargs="*",
        default=[],
        metavar="TERM",
        help="disambiguation terms ANDed into general queries (city, employer, job title)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="SearchAPI key; defaults to $SEARCHAPI_API_KEY / $SEARCHAPI_KEY",
    )
    parser.add_argument(
        "--engines",
        nargs="*",
        default=["google"],
        help="SearchAPI engines for general queries (google, bing, duckduckgo, yandex)",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=40,
        help="hard cap on requests; each one costs a SearchAPI credit (default: 40)",
    )
    parser.add_argument(
        "--num", type=int, default=10, help="results per query (default: 10)"
    )
    parser.add_argument(
        "--concurrency", type=int, default=5, help="parallel requests (default: 5)"
    )
    parser.add_argument(
        "--no-cyrillic",
        action="store_true",
        help="skip Cyrillic transliteration variants",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the query plan and exit without calling SearchAPI",
    )
    parser.add_argument(
        "--json", dest="json_path", help="write the full report to a JSON file"
    )
    parser.add_argument("--verbose", action="store_true", help="debug logging")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.dry_run:
        report = plan_search(
            args.name,
            context=args.context,
            engines=args.engines,
            max_queries=args.max_queries,
            with_cyrillic=not args.no_cyrillic,
        )
        print(render_report(report))
        print(
            f"\nDry run: {len(report.plan)} requests would be made (0 credits spent)."
        )
    else:
        api_key = get_api_key(args.api_key)
        if not api_key:
            print(
                "No SearchAPI key found. Pass --api-key or export SEARCHAPI_API_KEY.\n"
                "Use --dry-run to preview the query plan without a key.",
                file=sys.stderr,
            )
            return 2

        try:
            report = asyncio.run(
                run_name_search(
                    args.name,
                    api_key=api_key,
                    context=args.context,
                    engines=args.engines,
                    max_queries=args.max_queries,
                    concurrency=args.concurrency,
                    results_per_query=args.num,
                    with_cyrillic=not args.no_cyrillic,
                )
            )
        except SearchAPIError as error:
            print(f"SearchAPI error: {error}", file=sys.stderr)
            return 1

        print(render_report(report))

    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"\nJSON report saved to {args.json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
