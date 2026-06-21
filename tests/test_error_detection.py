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


def test_ignore_linkedin_999_status():
    assert detect_error_page("", 999, {}, ignore_403=False) is None
