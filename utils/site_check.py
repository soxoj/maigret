#!/usr/bin/env python3
"""
Site check utility for Maigret development.
Quickly test site availability, find valid usernames, and diagnose check issues.

Usage:
    python utils/site_check.py --site "SiteName" --check-claimed
    python utils/site_check.py --site "SiteName" --maigret           # Test via Maigret
    python utils/site_check.py --site "SiteName" --compare-methods   # aiohttp vs Maigret
    python utils/site_check.py --url "https://example.com/user/{username}" --test "john"
    python utils/site_check.py --site "SiteName" --find-user
    python utils/site_check.py --site "SiteName" --diagnose          # Full diagnosis
"""

import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import aiohttp
except ImportError:
    print("aiohttp not installed. Run: pip install aiohttp")
    sys.exit(1)

# Maigret imports (optional, for --maigret mode)
MAIGRET_AVAILABLE = False
try:
    from maigret.sites import MaigretDatabase, MaigretSite
    from maigret.checking import (
        SimpleAiohttpChecker,
        check_site_for_username,
        process_site_result,
        make_site_result,
    )
    from maigret.notify import QueryNotifyPrint
    from maigret.result import QueryStatus
    MAIGRET_AVAILABLE = True
except ImportError:
    pass


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

COMMON_USERNAMES = ["blue", "test", "admin", "user", "john", "alex", "david", "mike", "chris", "dan"]


class Colors:
    """ANSI color codes for terminal output."""
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def color(text: str, c: str) -> str:
    """Wrap text with color codes."""
    return f"{c}{text}{Colors.RESET}"


async def check_url_aiohttp(url: str, headers: dict = None, follow_redirects: bool = True,
                            timeout: int = 15, ssl_verify: bool = False) -> dict:
    """Check a URL using aiohttp and return detailed response info."""
    headers = headers or DEFAULT_HEADERS.copy()
    result = {
        "method": "aiohttp",
        "url": url,
        "status": None,
        "final_url": None,
        "redirects": [],
        "content_length": 0,
        "content": None,
        "title": None,
        "error": None,
        "error_type": None,
        "markers": {},
    }

    try:
        connector = aiohttp.TCPConnector(ssl=ssl_verify)
        timeout_obj = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout_obj) as session:
            async with session.get(url, headers=headers, allow_redirects=follow_redirects) as resp:
                result["status"] = resp.status
                result["final_url"] = str(resp.url)

                # Get redirect history
                if resp.history:
                    result["redirects"] = [str(r.url) for r in resp.history]

                # Read content
                try:
                    text = await resp.text()
                    result["content_length"] = len(text)
                    result["content"] = text

                    # Extract title
                    title_match = re.search(r'<title>([^<]*)</title>', text, re.IGNORECASE)
                    if title_match:
                        result["title"] = title_match.group(1).strip()[:100]

                    # Check common markers
                    text_lower = text.lower()
                    markers = {
                        "404_text": any(m in text_lower for m in ["not found", "404", "doesn't exist", "does not exist"]),
                        "profile_markers": any(m in text_lower for m in ["profile", "user", "member", "account"]),
                        "error_markers": any(m in text_lower for m in ["error", "banned", "suspended", "blocked"]),
                        "login_required": any(m in text_lower for m in ["log in", "login", "sign in", "signin"]),
                        "captcha": any(m in text_lower for m in ["captcha", "recaptcha", "challenge", "verify you"]),
                        "cloudflare": "cloudflare" in text_lower or "cf-ray" in text_lower,
                        "rate_limit": any(m in text_lower for m in ["rate limit", "too many requests", "429"]),
                    }
                    result["markers"] = markers

                    # First 500 chars of body for inspection
                    result["body_preview"] = text[:500].replace("\n", " ").strip()

                except Exception as e:
                    result["error"] = f"Content read error: {e}"
                    result["error_type"] = "content_error"

    except asyncio.TimeoutError:
        result["error"] = "Timeout"
        result["error_type"] = "timeout"
    except aiohttp.ClientError as e:
        result["error"] = f"Client error: {e}"
        result["error_type"] = "client_error"
    except Exception as e:
        result["error"] = f"Error: {e}"
        result["error_type"] = "unknown"

    return result


async def check_url_maigret(site: 'MaigretSite', username: str, logger=None) -> dict:
    """Check a URL using Maigret's checking mechanism."""
    if not MAIGRET_AVAILABLE:
        return {"error": "Maigret not available", "method": "maigret"}

    if logger is None:
        logger = logging.getLogger("site_check")
        logger.setLevel(logging.WARNING)

    result = {
        "method": "maigret",
        "url": None,
        "status": None,
        "status_str": None,
        "http_status": None,
        "final_url": None,
        "error": None,
        "error_type": None,
        "ids_data": None,
    }

    try:
        # Create query options
        options = {
            "parsing": False,
            "cookie_jar": None,
            "timeout": 15,
        }

        # Create a simple notifier
        class SilentNotify:
            def start(self, msg=None): pass
            def update(self, status, similar=False): pass
            def finish(self, msg=None, status=None): pass

        notifier = SilentNotify()

        # Run the check
        site_name, site_result = await check_site_for_username(
            site, username, options, logger, notifier
        )

        result["url"] = site_result.get("url_user")
        result["status"] = site_result.get("status")
        result["status_str"] = str(site_result.get("status"))
        result["http_status"] = site_result.get("http_status")
        result["ids_data"] = site_result.get("ids_data")

        # Check for errors
        status = site_result.get("status")
        if status and hasattr(status, 'error') and status.error:
            result["error"] = f"{status.error.type}: {status.error.desc}"
            result["error_type"] = str(status.error.type)

    except Exception as e:
        result["error"] = str(e)
        result["error_type"] = "exception"

    return result


async def find_valid_username(url_template: str, usernames: list = None, headers: dict = None) -> Optional[str]:
    """Try common usernames to find one that works."""
    usernames = usernames or COMMON_USERNAMES
    headers = headers or DEFAULT_HEADERS.copy()

    print(f"Testing {len(usernames)} usernames on {url_template}...")

    for username in usernames:
        url = url_template.replace("{username}", username)
        result = await check_url_aiohttp(url, headers)

        status = result["status"]
        markers = result.get("markers", {})

        # Good signs: 200 status, profile markers, no 404 text
        if status == 200 and not markers.get("404_text") and markers.get("profile_markers"):
            print(f"  {color('[+]', Colors.GREEN)} {username}: status={status}, has profile markers")
            return username
        elif status == 200 and not markers.get("404_text"):
            print(f"  {color('[?]', Colors.YELLOW)} {username}: status={status}, might work")
        else:
            print(f"  {color('[-]', Colors.RED)} {username}: status={status}")

    return None


async def compare_users_aiohttp(url_template: str, claimed: str, unclaimed: str = "noonewouldeverusethis7",
                                headers: dict = None) -> Tuple[dict, dict]:
    """Compare responses for claimed vs unclaimed usernames using aiohttp."""
    headers = headers or DEFAULT_HEADERS.copy()

    print(f"\n{'='*60}")
    print(f"Comparing: {color(claimed, Colors.GREEN)} vs {color(unclaimed, Colors.RED)}")
    print(f"URL template: {url_template}")
    print(f"Method: aiohttp")
    print(f"{'='*60}\n")

    url_claimed = url_template.replace("{username}", claimed)
    url_unclaimed = url_template.replace("{username}", unclaimed)

    result_claimed, result_unclaimed = await asyncio.gather(
        check_url_aiohttp(url_claimed, headers),
        check_url_aiohttp(url_unclaimed, headers)
    )

    def print_result(name, r, c):
        print(f"--- {color(name, c)} ---")
        print(f"  URL: {r['url']}")
        print(f"  Status: {color(str(r['status']), Colors.GREEN if r['status'] == 200 else Colors.RED)}")
        if r["redirects"]:
            print(f"  Redirects: {' -> '.join(r['redirects'])} -> {r['final_url']}")
        print(f"  Final URL: {r['final_url']}")
        print(f"  Content length: {r['content_length']}")
        print(f"  Title: {r['title']}")
        if r["error"]:
            print(f"  Error: {color(r['error'], Colors.RED)}")
        print(f"  Markers: {r['markers']}")
        print()

    print_result(f"CLAIMED ({claimed})", result_claimed, Colors.GREEN)
    print_result(f"UNCLAIMED ({unclaimed})", result_unclaimed, Colors.RED)

    # Analysis
    print(f"--- {color('ANALYSIS', Colors.CYAN)} ---")
    recommendations = []

    if result_claimed["status"] != result_unclaimed["status"]:
        print(f"  [!] Status codes differ: {result_claimed['status']} vs {result_unclaimed['status']}")
        recommendations.append(("status_code", f"Status codes: {result_claimed['status']} vs {result_unclaimed['status']}"))

    if result_claimed["final_url"] != result_unclaimed["final_url"]:
        print(f"  [!] Final URLs differ")
        recommendations.append(("response_url", "Final URLs differ"))

    if result_claimed["content_length"] != result_unclaimed["content_length"]:
        diff = abs(result_claimed["content_length"] - result_unclaimed["content_length"])
        print(f"  [!] Content length differs by {diff} bytes")
        recommendations.append(("message", f"Content differs by {diff} bytes"))

    if result_claimed["title"] != result_unclaimed["title"]:
        print(f"  [!] Titles differ:")
        print(f"      Claimed: {result_claimed['title']}")
        print(f"      Unclaimed: {result_unclaimed['title']}")
        recommendations.append(("message", f"Titles differ: '{result_claimed['title']}' vs '{result_unclaimed['title']}'"))

    # Check for problems
    if result_claimed.get("markers", {}).get("captcha"):
        print(f"  {color('[WARN]', Colors.YELLOW)} Captcha detected on claimed page")
    if result_claimed.get("markers", {}).get("cloudflare"):
        print(f"  {color('[WARN]', Colors.YELLOW)} Cloudflare protection detected")
    if result_claimed.get("markers", {}).get("login_required"):
        print(f"  {color('[WARN]', Colors.YELLOW)} Login may be required")

    if recommendations:
        print(f"\n  {color('Recommended checkType:', Colors.BOLD)} {recommendations[0][0]}")
    else:
        print(f"  {color('[!]', Colors.RED)} No clear difference found - site may need special handling")

    return result_claimed, result_unclaimed


async def compare_methods(site: 'MaigretSite', claimed: str, unclaimed: str) -> dict:
    """Compare aiohttp vs Maigret results for the same site."""
    if not MAIGRET_AVAILABLE:
        print(color("Maigret not available for comparison", Colors.RED))
        return {}

    print(f"\n{'='*60}")
    print(f"{color('METHOD COMPARISON', Colors.CYAN)}: aiohttp vs Maigret")
    print(f"Site: {site.name}")
    print(f"Claimed: {claimed}, Unclaimed: {unclaimed}")
    print(f"{'='*60}\n")

    # Build URL template
    url_template = site.url
    url_template = url_template.replace("{urlMain}", site.url_main or "")
    url_template = url_template.replace("{urlSubpath}", getattr(site, 'url_subpath', '') or "")

    headers = DEFAULT_HEADERS.copy()
    if hasattr(site, 'headers') and site.headers:
        headers.update(site.headers)

    # Run all checks in parallel
    url_claimed = url_template.replace("{username}", claimed)
    url_unclaimed = url_template.replace("{username}", unclaimed)

    aiohttp_claimed, aiohttp_unclaimed, maigret_claimed, maigret_unclaimed = await asyncio.gather(
        check_url_aiohttp(url_claimed, headers),
        check_url_aiohttp(url_unclaimed, headers),
        check_url_maigret(site, claimed),
        check_url_maigret(site, unclaimed),
    )

    def status_icon(status):
        if status == 200:
            return color("200", Colors.GREEN)
        elif status == 404:
            return color("404", Colors.YELLOW)
        elif status and status >= 400:
            return color(str(status), Colors.RED)
        return str(status)

    def maigret_status_icon(status_str):
        if "Claimed" in str(status_str):
            return color("Claimed", Colors.GREEN)
        elif "Available" in str(status_str):
            return color("Available", Colors.YELLOW)
        else:
            return color(str(status_str), Colors.RED)

    print(f"{'Method':<12} {'Username':<25} {'HTTP Status':<12} {'Result':<20}")
    print("-" * 70)
    print(f"{'aiohttp':<12} {claimed:<25} {status_icon(aiohttp_claimed['status']):<20} {'OK' if not aiohttp_claimed['error'] else aiohttp_claimed['error'][:20]}")
    print(f"{'aiohttp':<12} {unclaimed:<25} {status_icon(aiohttp_unclaimed['status']):<20} {'OK' if not aiohttp_unclaimed['error'] else aiohttp_unclaimed['error'][:20]}")
    print(f"{'Maigret':<12} {claimed:<25} {status_icon(maigret_claimed.get('http_status')):<20} {maigret_status_icon(maigret_claimed.get('status_str'))}")
    print(f"{'Maigret':<12} {unclaimed:<25} {status_icon(maigret_unclaimed.get('http_status')):<20} {maigret_status_icon(maigret_unclaimed.get('status_str'))}")

    # Check for discrepancies
    print(f"\n--- {color('DISCREPANCY ANALYSIS', Colors.CYAN)} ---")
    issues = []

    if aiohttp_claimed['status'] != maigret_claimed.get('http_status'):
        issues.append(f"HTTP status mismatch for claimed: aiohttp={aiohttp_claimed['status']}, Maigret={maigret_claimed.get('http_status')}")

    if aiohttp_unclaimed['status'] != maigret_unclaimed.get('http_status'):
        issues.append(f"HTTP status mismatch for unclaimed: aiohttp={aiohttp_unclaimed['status']}, Maigret={maigret_unclaimed.get('http_status')}")

    # Check Maigret detection correctness
    claimed_detected = "Claimed" in str(maigret_claimed.get('status_str', ''))
    unclaimed_detected = "Available" in str(maigret_unclaimed.get('status_str', ''))

    if not claimed_detected:
        issues.append(f"Maigret did NOT detect claimed user '{claimed}' as Claimed")
    if not unclaimed_detected:
        issues.append(f"Maigret did NOT detect unclaimed user '{unclaimed}' as Available")

    if issues:
        for issue in issues:
            print(f"  {color('[!]', Colors.RED)} {issue}")
    else:
        print(f"  {color('[OK]', Colors.GREEN)} Both methods agree on results")

    return {
        "aiohttp_claimed": aiohttp_claimed,
        "aiohttp_unclaimed": aiohttp_unclaimed,
        "maigret_claimed": maigret_claimed,
        "maigret_unclaimed": maigret_unclaimed,
        "issues": issues,
    }


async def diagnose_site(site_config: dict, site_name: str) -> dict:
    """Full diagnosis of a site configuration."""
    print(f"\n{'='*60}")
    print(f"{color('FULL SITE DIAGNOSIS', Colors.CYAN)}: {site_name}")
    print(f"{'='*60}\n")

    diagnosis = {
        "site_name": site_name,
        "issues": [],
        "warnings": [],
        "recommendations": [],
        "working": False,
    }

    # 1. Config analysis
    print(f"--- {color('1. CONFIGURATION', Colors.BOLD)} ---")
    check_type = site_config.get("checkType", "status_code")
    url = site_config.get("url", "")
    url_main = site_config.get("urlMain", "")
    claimed = site_config.get("usernameClaimed")
    unclaimed = site_config.get("usernameUnclaimed", "noonewouldeverusethis7")
    disabled = site_config.get("disabled", False)

    print(f"  checkType: {check_type}")
    print(f"  URL: {url}")
    print(f"  urlMain: {url_main}")
    print(f"  usernameClaimed: {claimed}")
    print(f"  disabled: {disabled}")

    if disabled:
        diagnosis["issues"].append("Site is disabled")
        print(f"  {color('[!]', Colors.YELLOW)} Site is disabled")

    if not claimed:
        diagnosis["issues"].append("No usernameClaimed defined")
        print(f"  {color('[!]', Colors.RED)} No usernameClaimed defined")
        return diagnosis

    # Build full URL
    url_template = url.replace("{urlMain}", url_main).replace("{urlSubpath}", site_config.get("urlSubpath", ""))

    headers = DEFAULT_HEADERS.copy()
    if site_config.get("headers"):
        headers.update(site_config["headers"])

    # 2. Connectivity test
    print(f"\n--- {color('2. CONNECTIVITY TEST', Colors.BOLD)} ---")
    url_claimed = url_template.replace("{username}", claimed)
    url_unclaimed = url_template.replace("{username}", unclaimed)

    result_claimed, result_unclaimed = await asyncio.gather(
        check_url_aiohttp(url_claimed, headers),
        check_url_aiohttp(url_unclaimed, headers)
    )

    print(f"  Claimed ({claimed}): status={result_claimed['status']}, error={result_claimed['error']}")
    print(f"  Unclaimed ({unclaimed}): status={result_unclaimed['status']}, error={result_unclaimed['error']}")

    # Check for common problems
    if result_claimed["error_type"] == "timeout":
        diagnosis["issues"].append("Timeout on claimed username")
    if result_unclaimed["error_type"] == "timeout":
        diagnosis["issues"].append("Timeout on unclaimed username")

    if result_claimed.get("markers", {}).get("cloudflare"):
        diagnosis["warnings"].append("Cloudflare protection detected")
    if result_claimed.get("markers", {}).get("captcha"):
        diagnosis["warnings"].append("Captcha detected")
    if result_claimed["status"] == 403:
        diagnosis["issues"].append("403 Forbidden - possible anti-bot protection")
    if result_claimed["status"] == 429:
        diagnosis["issues"].append("429 Rate Limited")

    # 3. Check type validation
    print(f"\n--- {color('3. CHECK TYPE VALIDATION', Colors.BOLD)} ---")

    if check_type == "status_code":
        if result_claimed["status"] == result_unclaimed["status"]:
            diagnosis["issues"].append(f"status_code check but same status ({result_claimed['status']}) for both")
            print(f"  {color('[FAIL]', Colors.RED)} Same status code for claimed and unclaimed: {result_claimed['status']}")
        else:
            print(f"  {color('[OK]', Colors.GREEN)} Status codes differ: {result_claimed['status']} vs {result_unclaimed['status']}")
            diagnosis["working"] = True

    elif check_type == "response_url":
        if result_claimed["final_url"] == result_unclaimed["final_url"]:
            diagnosis["issues"].append("response_url check but same final URL for both")
            print(f"  {color('[FAIL]', Colors.RED)} Same final URL for both")
        else:
            print(f"  {color('[OK]', Colors.GREEN)} Final URLs differ")
            diagnosis["working"] = True

    elif check_type == "message":
        presense_strs = site_config.get("presenseStrs", [])
        absence_strs = site_config.get("absenceStrs", [])

        print(f"  presenseStrs: {presense_strs}")
        print(f"  absenceStrs: {absence_strs}")

        claimed_content = result_claimed.get("content", "") or ""
        unclaimed_content = result_unclaimed.get("content", "") or ""

        # Check presenseStrs
        presense_found_claimed = any(s in claimed_content for s in presense_strs) if presense_strs else True
        presense_found_unclaimed = any(s in unclaimed_content for s in presense_strs) if presense_strs else True

        # Check absenceStrs
        absence_found_claimed = any(s in claimed_content for s in absence_strs) if absence_strs else False
        absence_found_unclaimed = any(s in unclaimed_content for s in absence_strs) if absence_strs else False

        print(f"  Claimed - presenseStrs found: {presense_found_claimed}, absenceStrs found: {absence_found_claimed}")
        print(f"  Unclaimed - presenseStrs found: {presense_found_unclaimed}, absenceStrs found: {absence_found_unclaimed}")

        if presense_strs and not presense_found_claimed:
            diagnosis["issues"].append(f"presenseStrs {presense_strs} not found in claimed page")
            print(f"  {color('[FAIL]', Colors.RED)} presenseStrs not found in claimed page")
        if absence_strs and absence_found_claimed:
            diagnosis["issues"].append(f"absenceStrs {absence_strs} found in claimed page (should not be)")
            print(f"  {color('[FAIL]', Colors.RED)} absenceStrs found in claimed page")
        if absence_strs and not absence_found_unclaimed:
            diagnosis["warnings"].append(f"absenceStrs not found in unclaimed page")
            print(f"  {color('[WARN]', Colors.YELLOW)} absenceStrs not found in unclaimed page")

        if presense_found_claimed and not absence_found_claimed and absence_found_unclaimed:
            print(f"  {color('[OK]', Colors.GREEN)} Message check should work correctly")
            diagnosis["working"] = True

    # 4. Recommendations
    print(f"\n--- {color('4. RECOMMENDATIONS', Colors.BOLD)} ---")

    if not diagnosis["working"]:
        # Suggest alternatives
        if result_claimed["status"] != result_unclaimed["status"]:
            diagnosis["recommendations"].append(f"Switch to checkType: status_code (status {result_claimed['status']} vs {result_unclaimed['status']})")
        if result_claimed["final_url"] != result_unclaimed["final_url"]:
            diagnosis["recommendations"].append("Switch to checkType: response_url")
        if result_claimed["title"] != result_unclaimed["title"]:
            diagnosis["recommendations"].append(f"Use title as marker: presenseStrs=['{result_claimed['title']}'] or absenceStrs=['{result_unclaimed['title']}']")

    if diagnosis["recommendations"]:
        for rec in diagnosis["recommendations"]:
            print(f"  -> {rec}")
    elif diagnosis["working"]:
        print(f"  {color('Site appears to be working correctly', Colors.GREEN)}")
    else:
        print(f"  {color('No clear fix found - site may need special handling or should be disabled', Colors.RED)}")

    # Summary
    print(f"\n--- {color('SUMMARY', Colors.BOLD)} ---")
    if diagnosis["issues"]:
        print(f"  Issues: {len(diagnosis['issues'])}")
        for issue in diagnosis["issues"]:
            print(f"    - {issue}")
    if diagnosis["warnings"]:
        print(f"  Warnings: {len(diagnosis['warnings'])}")
        for warn in diagnosis["warnings"]:
            print(f"    - {warn}")
    print(f"  Working: {color('YES', Colors.GREEN) if diagnosis['working'] else color('NO', Colors.RED)}")

    return diagnosis


def load_site_from_db(site_name: str) -> Tuple[Optional[dict], Optional['MaigretSite']]:
    """Load site config from data.json. Returns (config_dict, MaigretSite or None)."""
    db_path = Path(__file__).parent.parent / "maigret" / "resources" / "data.json"

    with open(db_path) as f:
        data = json.load(f)

    config = None
    if site_name in data["sites"]:
        config = data["sites"][site_name]
    else:
        # Try case-insensitive search
        for name, cfg in data["sites"].items():
            if name.lower() == site_name.lower():
                config = cfg
                site_name = name
                break

    if not config:
        return None, None

    # Also load MaigretSite if available
    maigret_site = None
    if MAIGRET_AVAILABLE:
        try:
            db = MaigretDatabase().load_from_path(db_path)
            maigret_site = db.sites_dict.get(site_name)
        except Exception:
            pass

    return config, maigret_site


async def main():
    parser = argparse.ArgumentParser(
        description="Site check utility for Maigret development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --site "VK" --check-claimed          # Test site with aiohttp
  %(prog)s --site "VK" --maigret                # Test site with Maigret
  %(prog)s --site "VK" --compare-methods        # Compare aiohttp vs Maigret
  %(prog)s --site "VK" --diagnose               # Full diagnosis
  %(prog)s --url "https://vk.com/{username}" --compare blue nobody123
  %(prog)s --site "VK" --find-user              # Find a valid username
        """
    )
    parser.add_argument("--site", "-s", help="Site name from data.json")
    parser.add_argument("--url", "-u", help="URL template with {username}")
    parser.add_argument("--test", "-t", help="Username to test")
    parser.add_argument("--compare", "-c", nargs=2, metavar=("CLAIMED", "UNCLAIMED"),
                        help="Compare two usernames")
    parser.add_argument("--find-user", "-f", action="store_true",
                        help="Find a valid username")
    parser.add_argument("--check-claimed", action="store_true",
                        help="Check if claimed username still works (aiohttp)")
    parser.add_argument("--maigret", "-m", action="store_true",
                        help="Test using Maigret's checker instead of aiohttp")
    parser.add_argument("--compare-methods", action="store_true",
                        help="Compare aiohttp vs Maigret results")
    parser.add_argument("--diagnose", "-d", action="store_true",
                        help="Full diagnosis of site configuration")
    parser.add_argument("--headers", help="Custom headers as JSON")
    parser.add_argument("--timeout", type=int, default=15, help="Request timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    url_template = None
    claimed = None
    unclaimed = "noonewouldeverusethis7"
    headers = DEFAULT_HEADERS.copy()
    site_config = None
    maigret_site = None

    # Load from site name
    if args.site:
        site_config, maigret_site = load_site_from_db(args.site)
        if not site_config:
            print(f"Site '{args.site}' not found in database")
            sys.exit(1)

        url_template = site_config.get("url", "")
        url_main = site_config.get("urlMain", "")
        url_subpath = site_config.get("urlSubpath", "")
        url_template = url_template.replace("{urlMain}", url_main).replace("{urlSubpath}", url_subpath)

        claimed = site_config.get("usernameClaimed")
        unclaimed = site_config.get("usernameUnclaimed", unclaimed)

        if site_config.get("headers"):
            headers.update(site_config["headers"])

        if not args.json:
            print(f"Loaded site: {args.site}")
            print(f"  URL: {url_template}")
            print(f"  Claimed: {claimed}")
            print(f"  CheckType: {site_config.get('checkType', 'unknown')}")
            print(f"  Disabled: {site_config.get('disabled', False)}")

    # Override with explicit URL
    if args.url:
        url_template = args.url

    # Custom headers
    if args.headers:
        headers.update(json.loads(args.headers))

    # Actions
    if args.diagnose:
        if not site_config:
            print("--diagnose requires --site")
            sys.exit(1)
        result = await diagnose_site(site_config, args.site)
        if args.json:
            print(json.dumps(result, indent=2, default=str))

    elif args.compare_methods:
        if not maigret_site:
            if not MAIGRET_AVAILABLE:
                print("Maigret imports not available")
            else:
                print("Could not load MaigretSite object")
            sys.exit(1)
        result = await compare_methods(maigret_site, claimed, unclaimed)
        if args.json:
            print(json.dumps(result, indent=2, default=str))

    elif args.maigret:
        if not maigret_site:
            if not MAIGRET_AVAILABLE:
                print("Maigret imports not available")
            else:
                print("Could not load MaigretSite object")
            sys.exit(1)

        print(f"\n--- Testing with Maigret ---")
        for username in [claimed, unclaimed]:
            result = await check_url_maigret(maigret_site, username)
            print(f"  {username}: status={result.get('status_str')}, http={result.get('http_status')}, error={result.get('error')}")

    elif args.find_user:
        if not url_template:
            print("--find-user requires --site or --url")
            sys.exit(1)
        result = await find_valid_username(url_template, headers=headers)
        if result:
            print(f"\n{color('Found valid username:', Colors.GREEN)} {result}")
        else:
            print(f"\n{color('No valid username found', Colors.RED)}")

    elif args.compare:
        if not url_template:
            print("--compare requires --site or --url")
            sys.exit(1)
        result = await compare_users_aiohttp(url_template, args.compare[0], args.compare[1], headers)
        if args.json:
            # Remove content field for JSON output (too large)
            for r in result:
                if isinstance(r, dict) and "content" in r:
                    del r["content"]
            print(json.dumps(result, indent=2, default=str))

    elif args.check_claimed and claimed:
        result = await compare_users_aiohttp(url_template, claimed, unclaimed, headers)

    elif args.test:
        if not url_template:
            print("--test requires --site or --url")
            sys.exit(1)
        url = url_template.replace("{username}", args.test)
        result = await check_url_aiohttp(url, headers, timeout=args.timeout)
        if "content" in result:
            del result["content"]  # Too large for display
        print(json.dumps(result, indent=2, default=str))

    else:
        # Default: check claimed username if available
        if url_template and claimed:
            await compare_users_aiohttp(url_template, claimed, unclaimed, headers)
        else:
            parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
