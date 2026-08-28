"""
Unit tests for error page detection helpers.
"""

from maigret.error_detection import detect_error_page
from maigret.errors import CheckError


def test_site_specific_error():
    err = detect_error_page(
        "this page is blocked",
        200,
        {"blocked": "Blocked by site"},
        ignore_403=False,
    )

    assert isinstance(err, CheckError)
    assert err.type == "Site-specific"


def test_http_403():
    err = detect_error_page("x", 403, {}, ignore_403=False)

    assert err.type == "Access denied"


def test_http_500():
    err = detect_error_page("x", 500, {}, ignore_403=False)

    assert err.type == "Server"


def test_no_error():
    assert detect_error_page("ok", 200, {}, ignore_403=False) is None


def test_http_429_is_rate_limit():
    err = detect_error_page("x", 429, {}, ignore_403=False)

    assert err.type == "Rate limited"


def test_ignore_linkedin_999_status():
    # 999 stays a pass-through on purpose, see detect_error_page.
    assert detect_error_page("", 999, {}, ignore_403=False) is None

def test_pow_challenge_pages_are_bot_protection():
    # Both serve a 2xx on every path, so without a marker every username
    # would read as claimed.
    anubis = detect_error_page(
        '<link rel="stylesheet" href="/.within.website/x/xess/xess.min.css">',
        200,
        {},
        ignore_403=False,
    )
    pow_js = detect_error_page(
        "window.POW_CHALLENGE_DATA={challenge_nonce:'2bafb0f5'};", 202, {}, ignore_403=False
    )

    assert anubis.type == "Bot protection"
    assert pow_js.type == "Bot protection"
