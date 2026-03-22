#!/usr/bin/env python3
"""
Mass site checking utility for Maigret development.
Check top-N sites from data.json and generate a report.

Usage:
    python utils/check_top_n.py --top 100                    # Check top 100 sites
    python utils/check_top_n.py --top 50 --parallel 10       # Check with 10 parallel requests
    python utils/check_top_n.py --top 100 --output report.json
    python utils/check_top_n.py --top 100 --fix              # Auto-fix simple issues
"""

import argparse
import asyncio
import json
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import aiohttp
except ImportError:
    print("aiohttp not installed. Run: pip install aiohttp")
    sys.exit(1)


class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def color(text: str, c: str) -> str:
    return f"{c}{text}{Colors.RESET}"


@dataclass
class SiteCheckResult:
    """Result of checking a single site."""
    site_name: str
    alexa_rank: int
    disabled: bool
    check_type: str

    # Status
    status: str = "unknown"  # working, broken, timeout, error, anti_bot, disabled

    # HTTP results
    claimed_http_status: Optional[int] = None
    unclaimed_http_status: Optional[int] = None
    claimed_error: Optional[str] = None
    unclaimed_error: Optional[str] = None

    # Issues detected
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    # Timing
    check_time_ms: int = 0


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


async def check_url(url: str, headers: dict, timeout: int = 15) -> dict:
    """Quick URL check returning status and basic info."""
    result = {
        "status": None,
        "final_url": None,
        "content_length": 0,
        "error": None,
        "error_type": None,
        "content": None,
        "markers": {},
    }

    try:
        connector = aiohttp.TCPConnector(ssl=False)
        timeout_obj = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout_obj) as session:
            async with session.get(url, headers=headers, allow_redirects=True) as resp:
                result["status"] = resp.status
                result["final_url"] = str(resp.url)

                try:
                    text = await resp.text()
                    result["content_length"] = len(text)
                    result["content"] = text

                    text_lower = text.lower()
                    result["markers"] = {
                        "404_text": any(m in text_lower for m in ["not found", "404", "doesn't exist"]),
                        "captcha": any(m in text_lower for m in ["captcha", "recaptcha", "challenge"]),
                        "cloudflare": "cloudflare" in text_lower,
                        "login": any(m in text_lower for m in ["log in", "login", "sign in"]),
                    }
                except Exception as e:
                    result["error"] = f"Content error: {e}"
                    result["error_type"] = "content"

    except asyncio.TimeoutError:
        result["error"] = "Timeout"
        result["error_type"] = "timeout"
    except aiohttp.ClientError as e:
        result["error"] = str(e)
        result["error_type"] = "client"
    except Exception as e:
        result["error"] = str(e)
        result["error_type"] = "unknown"

    return result


async def check_site(site_name: str, config: dict, timeout: int = 15) -> SiteCheckResult:
    """Check a single site and return detailed result."""
    start_time = time.time()

    result = SiteCheckResult(
        site_name=site_name,
        alexa_rank=config.get("alexaRank", 999999),
        disabled=config.get("disabled", False),
        check_type=config.get("checkType", "status_code"),
    )

    # Skip disabled sites
    if result.disabled:
        result.status = "disabled"
        return result

    # Build URL
    url_template = config.get("url", "")
    url_main = config.get("urlMain", "")
    url_subpath = config.get("urlSubpath", "")
    url_template = url_template.replace("{urlMain}", url_main).replace("{urlSubpath}", url_subpath)

    claimed = config.get("usernameClaimed")
    unclaimed = config.get("usernameUnclaimed", "noonewouldeverusethis7")

    if not claimed:
        result.status = "error"
        result.issues.append("No usernameClaimed defined")
        return result

    # Prepare headers
    headers = DEFAULT_HEADERS.copy()
    if config.get("headers"):
        headers.update(config["headers"])

    # Check both URLs
    url_claimed = url_template.replace("{username}", claimed)
    url_unclaimed = url_template.replace("{username}", unclaimed)

    try:
        claimed_result, unclaimed_result = await asyncio.gather(
            check_url(url_claimed, headers, timeout),
            check_url(url_unclaimed, headers, timeout),
        )
    except Exception as e:
        result.status = "error"
        result.issues.append(f"Check failed: {e}")
        return result

    result.claimed_http_status = claimed_result["status"]
    result.unclaimed_http_status = unclaimed_result["status"]
    result.claimed_error = claimed_result.get("error")
    result.unclaimed_error = unclaimed_result.get("error")

    # Categorize result
    if claimed_result["error_type"] == "timeout" or unclaimed_result["error_type"] == "timeout":
        result.status = "timeout"
        result.issues.append("Request timeout")

    elif claimed_result["status"] == 403 or claimed_result["status"] == 429:
        result.status = "anti_bot"
        result.issues.append(f"Anti-bot protection (HTTP {claimed_result['status']})")

    elif claimed_result.get("markers", {}).get("captcha"):
        result.status = "anti_bot"
        result.issues.append("Captcha detected")

    elif claimed_result.get("markers", {}).get("cloudflare"):
        result.status = "anti_bot"
        result.warnings.append("Cloudflare protection detected")

    elif claimed_result["error"] or unclaimed_result["error"]:
        result.status = "error"
        if claimed_result["error"]:
            result.issues.append(f"Claimed error: {claimed_result['error']}")
        if unclaimed_result["error"]:
            result.issues.append(f"Unclaimed error: {unclaimed_result['error']}")

    else:
        # Validate check type
        check_type = config.get("checkType", "status_code")

        if check_type == "status_code":
            if claimed_result["status"] == unclaimed_result["status"]:
                result.status = "broken"
                result.issues.append(f"Same status code ({claimed_result['status']}) for both")
                # Suggest fix
                if claimed_result["final_url"] != unclaimed_result["final_url"]:
                    result.recommendations.append("Switch to checkType: response_url")
            else:
                result.status = "working"

        elif check_type == "response_url":
            if claimed_result["final_url"] == unclaimed_result["final_url"]:
                result.status = "broken"
                result.issues.append("Same final URL for both")
                if claimed_result["status"] != unclaimed_result["status"]:
                    result.recommendations.append("Switch to checkType: status_code")
            else:
                result.status = "working"

        elif check_type == "message":
            presense_strs = config.get("presenseStrs", [])
            absence_strs = config.get("absenceStrs", [])

            claimed_content = claimed_result.get("content", "") or ""
            unclaimed_content = unclaimed_result.get("content", "") or ""

            presense_ok = not presense_strs or any(s in claimed_content for s in presense_strs)
            absence_claimed = absence_strs and any(s in claimed_content for s in absence_strs)
            absence_unclaimed = absence_strs and any(s in unclaimed_content for s in absence_strs)

            if presense_strs and not presense_ok:
                result.status = "broken"
                result.issues.append(f"presenseStrs not found: {presense_strs}")
                # Check if status_code would work
                if claimed_result["status"] != unclaimed_result["status"]:
                    result.recommendations.append(f"Switch to checkType: status_code ({claimed_result['status']} vs {unclaimed_result['status']})")
            elif absence_claimed:
                result.status = "broken"
                result.issues.append(f"absenceStrs found in claimed page")
            elif absence_strs and not absence_unclaimed:
                result.status = "broken"
                result.warnings.append("absenceStrs not found in unclaimed page")
            else:
                result.status = "working"

        else:
            result.status = "unknown"
            result.warnings.append(f"Unknown checkType: {check_type}")

    result.check_time_ms = int((time.time() - start_time) * 1000)
    return result


def load_sites(db_path: Path) -> Dict[str, dict]:
    """Load all sites from data.json."""
    with open(db_path) as f:
        data = json.load(f)
    return data.get("sites", {})


def get_top_sites(sites: Dict[str, dict], n: int) -> List[Tuple[str, dict]]:
    """Get top N sites by Alexa rank."""
    ranked = []
    for name, config in sites.items():
        rank = config.get("alexaRank", 999999)
        ranked.append((name, config, rank))

    ranked.sort(key=lambda x: x[2])
    return [(name, config) for name, config, _ in ranked[:n]]


async def check_sites_batch(sites: List[Tuple[str, dict]], parallel: int = 5,
                            timeout: int = 15, progress_callback=None) -> List[SiteCheckResult]:
    """Check multiple sites with parallelism control."""
    results = []
    semaphore = asyncio.Semaphore(parallel)

    async def check_with_semaphore(name, config, index):
        async with semaphore:
            if progress_callback:
                progress_callback(index, len(sites), name)
            return await check_site(name, config, timeout)

    tasks = [
        check_with_semaphore(name, config, i)
        for i, (name, config) in enumerate(sites)
    ]

    results = await asyncio.gather(*tasks)
    return results


def print_progress(current: int, total: int, site_name: str):
    """Print progress indicator."""
    pct = int(current / total * 100)
    bar_width = 30
    filled = int(bar_width * current / total)
    bar = "█" * filled + "░" * (bar_width - filled)
    print(f"\r[{bar}] {pct:3d}% ({current}/{total}) {site_name:<30}", end="", flush=True)


def generate_report(results: List[SiteCheckResult]) -> dict:
    """Generate a summary report from check results."""
    report = {
        "summary": {
            "total": len(results),
            "working": 0,
            "broken": 0,
            "disabled": 0,
            "timeout": 0,
            "anti_bot": 0,
            "error": 0,
            "unknown": 0,
        },
        "by_status": defaultdict(list),
        "issues": [],
        "recommendations": [],
    }

    for r in results:
        report["summary"][r.status] = report["summary"].get(r.status, 0) + 1
        report["by_status"][r.status].append(r.site_name)

        if r.issues:
            report["issues"].append({
                "site": r.site_name,
                "rank": r.alexa_rank,
                "issues": r.issues,
            })

        if r.recommendations:
            report["recommendations"].append({
                "site": r.site_name,
                "rank": r.alexa_rank,
                "recommendations": r.recommendations,
            })

    return report


def print_report(report: dict, results: List[SiteCheckResult]):
    """Print a formatted report to console."""
    summary = report["summary"]

    print(f"\n{'='*60}")
    print(f"{color('SITE CHECK REPORT', Colors.CYAN)}")
    print(f"{'='*60}\n")

    print(f"{color('SUMMARY:', Colors.BOLD)}")
    print(f"  Total sites checked: {summary['total']}")
    print(f"  {color('Working:', Colors.GREEN)} {summary['working']}")
    print(f"  {color('Broken:', Colors.RED)} {summary['broken']}")
    print(f"  {color('Disabled:', Colors.YELLOW)} {summary['disabled']}")
    print(f"  {color('Timeout:', Colors.YELLOW)} {summary['timeout']}")
    print(f"  {color('Anti-bot:', Colors.YELLOW)} {summary['anti_bot']}")
    print(f"  {color('Error:', Colors.RED)} {summary['error']}")

    # Broken sites
    if report["by_status"]["broken"]:
        print(f"\n{color('BROKEN SITES:', Colors.RED)}")
        for site in report["by_status"]["broken"][:20]:
            r = next(x for x in results if x.site_name == site)
            print(f"  - {site} (rank {r.alexa_rank}): {', '.join(r.issues)}")
        if len(report["by_status"]["broken"]) > 20:
            print(f"  ... and {len(report['by_status']['broken']) - 20} more")

    # Timeout sites
    if report["by_status"]["timeout"]:
        print(f"\n{color('TIMEOUT SITES:', Colors.YELLOW)}")
        for site in report["by_status"]["timeout"][:10]:
            print(f"  - {site}")
        if len(report["by_status"]["timeout"]) > 10:
            print(f"  ... and {len(report['by_status']['timeout']) - 10} more")

    # Anti-bot sites
    if report["by_status"]["anti_bot"]:
        print(f"\n{color('ANTI-BOT PROTECTED:', Colors.YELLOW)}")
        for site in report["by_status"]["anti_bot"][:10]:
            r = next(x for x in results if x.site_name == site)
            print(f"  - {site}: {', '.join(r.issues)}")
        if len(report["by_status"]["anti_bot"]) > 10:
            print(f"  ... and {len(report['by_status']['anti_bot']) - 10} more")

    # Recommendations
    if report["recommendations"]:
        print(f"\n{color('RECOMMENDATIONS:', Colors.CYAN)}")
        for rec in report["recommendations"][:15]:
            print(f"  {rec['site']} (rank {rec['rank']}):")
            for r in rec["recommendations"]:
                print(f"    -> {r}")
        if len(report["recommendations"]) > 15:
            print(f"  ... and {len(report['recommendations']) - 15} more")


async def main():
    parser = argparse.ArgumentParser(
        description="Mass site checking for Maigret",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--top", "-n", type=int, default=100,
                        help="Check top N sites by Alexa rank (default: 100)")
    parser.add_argument("--parallel", "-p", type=int, default=5,
                        help="Number of parallel requests (default: 5)")
    parser.add_argument("--timeout", "-t", type=int, default=15,
                        help="Request timeout in seconds (default: 15)")
    parser.add_argument("--output", "-o", help="Output JSON report to file")
    parser.add_argument("--include-disabled", action="store_true",
                        help="Include disabled sites in results")
    parser.add_argument("--only-broken", action="store_true",
                        help="Only show broken sites")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON only")

    args = parser.parse_args()

    # Load sites
    db_path = Path(__file__).parent.parent / "maigret" / "resources" / "data.json"
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)

    sites = load_sites(db_path)
    top_sites = get_top_sites(sites, args.top)

    if not args.json:
        print(f"Checking top {len(top_sites)} sites (parallel={args.parallel}, timeout={args.timeout}s)...")
        print()

    # Run checks
    progress = print_progress if not args.json else None
    results = await check_sites_batch(top_sites, args.parallel, args.timeout, progress)

    if not args.json:
        print()  # Clear progress line

    # Filter results
    if not args.include_disabled:
        results = [r for r in results if r.status != "disabled"]
    if args.only_broken:
        results = [r for r in results if r.status in ("broken", "error", "timeout")]

    # Generate report
    report = generate_report(results)

    # Output
    if args.json:
        output = {
            "report": report,
            "results": [asdict(r) for r in results],
        }
        print(json.dumps(output, indent=2))
    else:
        print_report(report, results)

    # Save to file
    if args.output:
        output = {
            "report": report,
            "results": [asdict(r) for r in results],
        }
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
