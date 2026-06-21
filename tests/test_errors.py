import pytest
from maigret.checking import _is_dns_error
from maigret.errors import notify_about_errors, CheckError, solution_of, threshold_for, THRESHOLD
from maigret.result import MaigretCheckResult, MaigretCheckStatus


def test_notify_about_errors():
    results = {
        'site1': {
            'status': MaigretCheckResult(
                '', '', '', MaigretCheckStatus.UNKNOWN, error=CheckError('Captcha')
            )
        },
        'site2': {
            'status': MaigretCheckResult(
                '',
                '',
                '',
                MaigretCheckStatus.UNKNOWN,
                error=CheckError('Bot protection'),
            )
        },
        'site3': {
            'status': MaigretCheckResult(
                '',
                '',
                '',
                MaigretCheckStatus.UNKNOWN,
                error=CheckError('Access denied'),
            )
        },
        'site4': {
            'status': MaigretCheckResult(
                '', '', '', MaigretCheckStatus.CLAIMED, error=None
            )
        },
    }

    notifications = notify_about_errors(results, query_notify=None, show_statistics=True)

    # Notifications now carry the actionable advice as a separate 3rd tuple
    # element so notify.warning can render it in normal weight (the count
    # line stays bold).
    expected_output = [
        (
            'Too many errors of type "Captcha" (25.0%)',
            '!',
            'Try to switch to another ip address or to use service cookies',
        ),
        (
            'Too many errors of type "Bot protection" (25.0%)',
            '!',
            'Try to switch to another ip address',
        ),
        (
            'Too many errors of type "Access denied" (25.0%)',
            '!',
            "It's recommended to use --cloudflare-bypass or proxy, "
            "e.g. https://vaultproxies.net/maigret",
        ),
        ('Verbose error statistics:', '-'),
        ('Captcha: 25.0%', '!'),
        ('Bot protection: 25.0%', '!'),
        ('Access denied: 25.0%', '!'),
        ('You can see detailed site check errors with a flag `--print-errors`', '-'),
    ]
    assert notifications == expected_output


def test_below_threshold_non_integer_percent_stays_silent():
    # 1 Captcha error out of 40 sites = 2.5%, below the 3% threshold. The raw
    # fraction must be scaled to a percentage before rounding; rounding the
    # fraction first turned 2.5% into 3.0% and fired a spurious warning.
    results = {
        'cap': {
            'status': MaigretCheckResult(
                '', '', '', MaigretCheckStatus.UNKNOWN, error=CheckError('Captcha')
            )
        }
    }
    for i in range(39):
        results[f'ok{i}'] = {
            'status': MaigretCheckResult(
                '', '', '', MaigretCheckStatus.CLAIMED, error=None
            )
        }

    notifications = notify_about_errors(results, query_notify=None)

    assert all('Captcha' not in n[0] for n in notifications), notifications


# Tests for the DNS-vs-generic split of "Connecting failure" introduced for
# https://github.com/soxoj/maigret/issues/2688 — when the user's machine
# cannot reach a DNS server, the result was previously reported as plain
# "Connecting failure" with the misleading advice "decrease number of
# parallel connections" (irrelevant when the network layer is broken).


class _FakeDNSError(Exception):
    """Stand-in for older aiohttp versions where ClientConnectorDNSError
    doesn't exist. _is_dns_error must still classify these via substring."""


@pytest.mark.parametrize(
    "message",
    [
        # exact wording from the issue #2688 trace (Windows + aiohttp 3.13)
        "Cannot connect to host www.facebook.com:443 ssl:default [Could not contact DNS servers]",
        # other OS / resolver wordings observed in the wild — case-insensitive
        "Cannot connect to host x.example:443 ssl:default [Name or service not known]",
        "[Errno 8] nodename nor servname provided, or not known",
        "[Errno -3] Temporary failure in name resolution",
        "getaddrinfo failed",
        # mixed case must still match
        "Cannot connect to host y.example:443 ssl:default [COULD NOT CONTACT DNS SERVERS]",
    ],
)
def test_is_dns_error_matches_known_resolver_wordings(message):
    assert _is_dns_error(_FakeDNSError(message)) is True


@pytest.mark.parametrize(
    "message",
    [
        # genuine non-DNS connection failures must NOT be misclassified
        "Cannot connect to host www.example.com:443 ssl:default [Connection refused]",
        "Cannot connect to host www.example.com:443 ssl:default [Network is unreachable]",
        "[Errno 110] Connection timed out",
        "Connection reset by peer",
    ],
)
def test_is_dns_error_does_not_misfire_on_other_connection_failures(message):
    assert _is_dns_error(_FakeDNSError(message)) is False


def test_is_dns_error_uses_subclass_when_available():
    """When aiohttp >=3.10 is installed, isinstance(ClientConnectorDNSError)
    must be the primary classifier — independent of the message text, so a
    DNS error with an unfamiliar wording is still caught."""
    try:
        from aiohttp.client_exceptions import ClientConnectorDNSError
    except ImportError:
        pytest.skip("aiohttp < 3.10 — no ClientConnectorDNSError subclass to test")

    # Build a minimal ClientConnectorDNSError using its real parent signature.
    # We don't want to instantiate the full aiohttp ConnectionKey — sub-class
    # the exception to bypass the constructor and verify the isinstance path.
    class _Sub(ClientConnectorDNSError):
        def __init__(self, msg):
            Exception.__init__(self, msg)

    assert _is_dns_error(_Sub("something the substring matcher would not catch")) is True


def test_connecting_failure_dns_has_specific_recommendation():
    """The new error class must have a DNS-specific recommendation that
    does NOT mention parallel connections (the old, misleading advice),
    AND must point at the actual fix (--dns-resolver threaded)."""
    advice = solution_of("Connecting failure (DNS)")
    assert advice  # not empty
    assert "DNS" in advice
    # the misleading advice from the original "Connecting failure" must NOT
    # leak into the DNS-class recommendation
    assert "parallel connections" not in advice
    # and it must point at the actual fix Maigret can offer
    assert "--dns-resolver threaded" in advice
    # the user-side fallbacks should also be mentioned
    assert "internet connection" in advice.lower()


def test_dns_failures_get_their_own_recommendation_in_notifications():
    """End-to-end: a result set dominated by DNS errors must surface the
    DNS-specific advice, not the generic "Connecting failure" one. The
    advice now lives in a separate tuple slot so notify.warning can render
    it without the bold/bright treatment applied to the count line."""
    results = {
        f'site{i}': {
            'status': MaigretCheckResult(
                '', '', '', MaigretCheckStatus.UNKNOWN,
                error=CheckError('Connecting failure (DNS)', 'Could not contact DNS servers'),
            )
        }
        for i in range(10)
    }

    notifications = notify_about_errors(results, query_notify=None, show_statistics=False)

    assert notifications
    first = notifications[0]
    # 3-tuple now: (count line, symbol, advice)
    assert len(first) == 3
    assert 'Connecting failure (DNS)' in first[0]
    assert first[1] == '!'
    # notify_about_errors passes the advice through .capitalize() before
    # display, which lowercases everything after the first character — so
    # compare case-insensitively.
    advice_ci = first[2].lower()
    assert 'dns resolution failed' in advice_ci
    assert 'parallel connections' not in advice_ci
    # The count line itself must NOT carry the advice — that's what lets
    # notify.warning render the two pieces with different weights.
    assert 'dns resolution failed' not in first[0].lower()


def test_webgate_unavailable_advice_points_at_flaresolverr_and_the_opt_out():
    """When the 'Too many errors' summary is dominated by 'Webgate
    unavailable', the user almost certainly opted into cloudflare_bypass
    and the solver isn't running. The advice must:
      - reaffirm that cloudflare_bypass is enabled (so the user knows it's
        their own config, not Maigret auto-trying it),
      - give the FlareSolverr docker one-liner as the most common fix,
      - mention the opt-out (disable cloudflare_bypass) for users who do
        not want to run a solver at all."""
    results = {
        f'cf-site{i}': {
            'status': MaigretCheckResult(
                '', '', '', MaigretCheckStatus.UNKNOWN,
                error=CheckError('Webgate unavailable', 'solver at http://localhost:8191/v1 unreachable'),
            )
        }
        for i in range(10)
    }

    notifications = notify_about_errors(results, query_notify=None, show_statistics=False)
    assert notifications
    first = notifications[0]
    assert len(first) == 3
    assert 'Webgate unavailable' in first[0]

    advice = first[2].lower()
    assert 'cloudflare_bypass is enabled' in advice
    assert 'flaresolverr' in advice
    # Specific docker invocation, not a vague "run a solver"
    assert 'docker run' in advice
    # Escape hatch: turning the feature off entirely
    assert 'set `cloudflare_bypass.enabled` to false' in advice


# Per-error-type threshold overrides. Default is 3%; DNS failures need 10%
# because the database always contains a few sites with dead DNS records,
# and we don't want to recommend "configure your DNS" when only 3% of
# checks fail (almost certainly data rot, not the user's machine).


def test_default_threshold_unchanged_for_unknown_types():
    assert threshold_for('Captcha') == THRESHOLD
    assert threshold_for('Bot protection') == THRESHOLD
    assert threshold_for('Some unknown type') == THRESHOLD


def test_dns_threshold_is_higher_than_default():
    assert threshold_for('Connecting failure (DNS)') == 10
    assert threshold_for('Connecting failure (DNS)') > THRESHOLD


def _results_with_dns_errors(dns_count, total):
    """Build a result set with `dns_count` DNS errors and (total - dns_count)
    successful CLAIMED results, so the DNS error rate is exactly
    dns_count/total."""
    results = {}
    for i in range(dns_count):
        results[f'dead-site{i}'] = {
            'status': MaigretCheckResult(
                '', '', '', MaigretCheckStatus.UNKNOWN,
                error=CheckError('Connecting failure (DNS)', 'no DNS'),
            )
        }
    for i in range(total - dns_count):
        results[f'good-site{i}'] = {
            'status': MaigretCheckResult('', '', '', MaigretCheckStatus.CLAIMED)
        }
    return results


def test_dns_errors_below_10_percent_are_silenced():
    """5% DNS error rate = a handful of dead domains in a normal batch.
    Maigret must NOT bother the user with VPN/firewall troubleshooting at
    this rate — it would be wrong advice for nearly every user."""
    results = _results_with_dns_errors(dns_count=5, total=100)
    notifications = notify_about_errors(results, query_notify=None)
    # No notification should mention DNS — the only signal would be the
    # "Verbose error statistics:" block, which we did not request here.
    assert all('Connecting failure (DNS)' not in (n[0] if n else '') for n in notifications)


def test_dns_errors_at_10_percent_or_above_fire_the_warning():
    """10% DNS error rate = systemic, almost certainly the user's resolver.
    THIS is when the advice is helpful."""
    results = _results_with_dns_errors(dns_count=10, total=100)
    notifications = notify_about_errors(results, query_notify=None)
    assert notifications, "Expected at least one warning at 10% DNS error rate"
    assert any('Connecting failure (DNS)' in n[0] for n in notifications)


def test_non_dns_errors_still_fire_at_3_percent():
    """The DNS threshold override must NOT change behaviour for other error
    types — Captcha at 3% should still surface as before."""
    results = {}
    for i in range(3):
        results[f'cap{i}'] = {
            'status': MaigretCheckResult(
                '', '', '', MaigretCheckStatus.UNKNOWN,
                error=CheckError('Captcha', 'cf'),
            )
        }
    for i in range(97):
        results[f'ok{i}'] = {
            'status': MaigretCheckResult('', '', '', MaigretCheckStatus.CLAIMED)
        }
    notifications = notify_about_errors(results, query_notify=None)
    assert any('Captcha' in n[0] for n in notifications)
