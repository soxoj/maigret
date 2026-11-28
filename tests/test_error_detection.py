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


def test_linkedin_999_is_an_error_not_an_absence():
    # LinkedIn serves 999 to blocked clients for existing and non-existing
    # profiles alike. Passing it through to the status_code branch reported
    # every profile as free, so a blocked user was told that a real account
    # does not exist.
    err = detect_error_page("", 999, {}, ignore_403=False)
    assert err is not None
    assert err.type == "Access denied"


def test_google_recaptcha_interstitial_is_a_captcha():
    # Answers 200 on every path, so without a marker every username reads as
    # claimed on a status_code site.
    err = detect_error_page(
        '<title>Checking your browser - reCAPTCHA</title>'
        '<script src="https://www.google.com/recaptcha/challengepage/x"></script>',
        200, {}, ignore_403=False,
    )
    assert err is not None
    assert err.type == "Captcha"


def test_page_embedding_a_recaptcha_widget_is_not_an_error():
    # A login form that loads the reCAPTCHA script is an ordinary page; only
    # the challenge interstitial counts as a block.
    assert detect_error_page(
        '<form><script src="https://www.google.com/recaptcha/enterprise.js"></script></form>',
        200, {}, ignore_403=False,
    ) is None


def test_imunify360_webshield_interstitial_is_bot_protection():
    # Serves HTTP 200 on every path, so without a marker absence-only and
    # status_code sites report every username as claimed.
    err = detect_error_page(
        "<title>One moment, please...</title>"
        "<div id='text'>Please wait while your request is being verified...</div>"
        "<script>P='wsidchk',l='/z0f76a1d14fd21a8fb5fd0d03e0fdc3d3cedae52f';</script>",
        200,
        {},
        ignore_403=False,
    )
    assert err is not None
    assert err.type == "Bot protection"
    assert err.desc == "Imunify360 WebShield"


def test_stile_challenge_interstitial_is_bot_protection():
    # Redirects to /.stile/challenge with HTTP 200 on challenged probes.
    err = detect_error_page(
        '<title>Checking your browser</title>'
        '<meta http-equiv="refresh" content="0; url=/.stile/challenge/verify?nojs=1&amp;nonce=abc">',
        200,
        {},
        ignore_403=False,
    )
    assert err is not None
    assert err.type == "Bot protection"
    assert err.desc == "Stile challenge"


def test_ordinary_page_mentioning_browser_check_is_not_an_error():
    # Generic wording without the vendor challenge endpoint must not trip
    # bot-protection detection on normal profile or forum pages.
    assert (
        detect_error_page(
            "<title>One moment, please</title><p>Checking your browser tips on stile doors</p>",
            200,
            {},
            ignore_403=False,
        )
        is None
    )
