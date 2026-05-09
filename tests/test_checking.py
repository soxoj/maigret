from argparse import ArgumentTypeError

from mock import Mock
import pytest

from maigret import search
from maigret.checking import (
    detect_error_page,
    extract_ids_data,
    parse_usernames,
    update_results_info,
    get_failed_sites,
    timeout_check,
    debug_response_logging,
    process_site_result,
)
from maigret.errors import CheckError
from maigret.result import MaigretCheckResult, MaigretCheckStatus
from maigret.sites import MaigretSite


def site_result_except(server, username, **kwargs):
    query = f'id={username}'
    server.expect_request('/url', query_string=query).respond_with_data(**kwargs)


@pytest.mark.slow
@pytest.mark.asyncio
async def test_checking_by_status_code(httpserver, local_test_db):
    sites_dict = local_test_db.sites_dict

    site_result_except(httpserver, 'claimed', status=200)
    site_result_except(httpserver, 'unclaimed', status=404)

    result = await search('claimed', site_dict=sites_dict, logger=Mock())
    assert result['StatusCode']['status'].is_found() is True

    result = await search('unclaimed', site_dict=sites_dict, logger=Mock())
    assert result['StatusCode']['status'].is_found() is False


@pytest.mark.slow
@pytest.mark.asyncio
async def test_checking_by_message_positive_full(httpserver, local_test_db):
    sites_dict = local_test_db.sites_dict

    site_result_except(httpserver, 'claimed', response_data="user profile")
    site_result_except(httpserver, 'unclaimed', response_data="404 not found")

    result = await search('claimed', site_dict=sites_dict, logger=Mock())
    assert result['Message']['status'].is_found() is True

    result = await search('unclaimed', site_dict=sites_dict, logger=Mock())
    assert result['Message']['status'].is_found() is False


@pytest.mark.slow
@pytest.mark.asyncio
async def test_checking_by_message_positive_part(httpserver, local_test_db):
    sites_dict = local_test_db.sites_dict

    site_result_except(httpserver, 'claimed', response_data="profile")
    site_result_except(httpserver, 'unclaimed', response_data="404")

    result = await search('claimed', site_dict=sites_dict, logger=Mock())
    assert result['Message']['status'].is_found() is True

    result = await search('unclaimed', site_dict=sites_dict, logger=Mock())
    assert result['Message']['status'].is_found() is False


@pytest.mark.slow
@pytest.mark.asyncio
async def test_checking_by_message_negative(httpserver, local_test_db):
    sites_dict = local_test_db.sites_dict

    site_result_except(httpserver, 'claimed', response_data="")
    site_result_except(httpserver, 'unclaimed', response_data="user 404")

    result = await search('claimed', site_dict=sites_dict, logger=Mock())
    assert result['Message']['status'].is_found() is False

    result = await search('unclaimed', site_dict=sites_dict, logger=Mock())
    assert result['Message']['status'].is_found() is True


# ---- Pure-function unit tests (no network) ----


def test_detect_error_page_site_specific():
    err = detect_error_page(
        "Please enable JavaScript to proceed",
        200,
        {"Please enable JavaScript to proceed": "Scraping protection"},
        ignore_403=False,
    )
    assert err is not None
    assert err.type == "Site-specific"
    assert err.desc == "Scraping protection"


def test_detect_error_page_403():
    err = detect_error_page("some body", 403, {}, ignore_403=False)
    assert err is not None
    assert err.type == "Access denied"


def test_detect_error_page_403_ignored():
    # XenForo engine uses ignore403 because member-not-found also returns 403
    assert detect_error_page("not found body", 403, {}, ignore_403=True) is None


def test_detect_error_page_999_linkedin():
    # LinkedIn returns 999 on bot suspicion — must NOT be reported as Server error
    assert detect_error_page("", 999, {}, ignore_403=False) is None


def test_detect_error_page_500():
    err = detect_error_page("", 503, {}, ignore_403=False)
    assert err is not None
    assert err.type == "Server"
    assert "503" in err.desc


def test_detect_error_page_ok():
    assert detect_error_page("hello world", 200, {}, ignore_403=False) is None


def test_parse_usernames_single_username():
    logger = Mock()
    result = parse_usernames({"profile_username": "alice"}, logger)
    assert result == {"alice": "username"}


def test_parse_usernames_list_of_usernames():
    logger = Mock()
    result = parse_usernames({"other_usernames": "['alice', 'bob']"}, logger)
    assert result == {"alice": "username", "bob": "username"}


def test_parse_usernames_malformed_list():
    logger = Mock()
    result = parse_usernames({"other_usernames": "not-a-list"}, logger)
    # should swallow the error and just return empty
    assert result == {}
    assert logger.warning.called


def test_parse_usernames_supported_id():
    logger = Mock()
    # "telegram" is in SUPPORTED_IDS per socid_extractor
    from maigret.checking import SUPPORTED_IDS
    if SUPPORTED_IDS:
        key = next(iter(SUPPORTED_IDS))
        result = parse_usernames({key: "some_value"}, logger)
        assert result.get("some_value") == key


def test_update_results_info_links():
    info = {"username": "test"}
    result = update_results_info(
        info,
        {"links": "['https://example.com/a', 'https://example.com/b']", "website": "https://example.com/w"},
        {"alice": "username"},
    )
    assert result["ids_usernames"] == {"alice": "username"}
    assert "https://example.com/w" in result["ids_links"]
    assert "https://example.com/a" in result["ids_links"]


def test_update_results_info_no_website():
    info = {}
    result = update_results_info(info, {"links": "[]"}, {})
    assert result["ids_links"] == []


def test_extract_ids_data_bad_html_returns_empty():
    logger = Mock()
    # Random HTML should not raise — returns {} if nothing matches
    out = extract_ids_data("<html><body>nothing special</body></html>", logger, Mock(name="Site"))
    assert isinstance(out, dict)


def test_get_failed_sites_filters_permanent_errors():
    # Temporary errors (Request timeout, Connecting failure, etc.) are retryable → returned.
    # Permanent ones (Captcha, Access denied, etc.) and results without error → filtered out.
    good_status = MaigretCheckResult("u", "S1", "https://s1", MaigretCheckStatus.CLAIMED)
    timeout_err = MaigretCheckResult(
        "u", "S2", "https://s2", MaigretCheckStatus.UNKNOWN,
        error=CheckError("Request timeout", "slow server"),
    )
    captcha_err = MaigretCheckResult(
        "u", "S3", "https://s3", MaigretCheckStatus.UNKNOWN,
        error=CheckError("Captcha", "Cloudflare"),
    )
    results = {
        "S1": {"status": good_status},
        "S2": {"status": timeout_err},
        "S3": {"status": captcha_err},
        "S4": {},  # no status at all
    }
    failed = get_failed_sites(results)
    # Only the temporary-error site is retry-worthy
    assert failed == ["S2"]


def test_timeout_check_valid():
    assert timeout_check("2.5") == 2.5
    assert timeout_check("30") == 30.0


def test_timeout_check_invalid():
    with pytest.raises(ArgumentTypeError):
        timeout_check("abc")
    with pytest.raises(ArgumentTypeError):
        timeout_check("0")
    with pytest.raises(ArgumentTypeError):
        timeout_check("-1")


def test_debug_response_logging_writes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    debug_response_logging("https://example.com", "<html>hi</html>", 200, None)
    out = (tmp_path / "debug.log").read_text()
    assert "https://example.com" in out
    assert "200" in out


def test_debug_response_logging_no_response(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    debug_response_logging("https://example.com", None, None, CheckError("Timeout"))
    out = (tmp_path / "debug.log").read_text()
    assert "No response" in out


def _make_site(data_overrides=None):
    base = {
        "url": "https://x/{username}",
        "urlMain": "https://x",
        "checkType": "status_code",
        "usernameClaimed": "a",
        "usernameUnclaimed": "b",
    }
    if data_overrides:
        base.update(data_overrides)
    return MaigretSite("TestSite", base)


def test_process_site_result_no_response_returns_info():
    site = _make_site()
    info = {"username": "a", "parsing_enabled": False, "url_user": "https://x/a"}
    out = process_site_result(None, Mock(), Mock(), info, site)
    assert out is info


def test_process_site_result_status_already_set():
    site = _make_site()
    pre = MaigretCheckResult("a", "S", "u", MaigretCheckStatus.ILLEGAL)
    info = {"username": "a", "parsing_enabled": False, "status": pre, "url_user": "u"}
    # Since status is already set, function returns without changes
    out = process_site_result(("<html/>", 200, None), Mock(), Mock(), info, site)
    assert out["status"] is pre


def test_process_site_result_status_code_claimed():
    site = _make_site({"checkType": "status_code"})
    info = {"username": "a", "parsing_enabled": False, "url_user": "https://x/a"}
    out = process_site_result(("<html/>", 200, None), Mock(), Mock(), info, site)
    assert out["status"].status == MaigretCheckStatus.CLAIMED
    assert out["http_status"] == 200


def test_process_site_result_status_code_available():
    site = _make_site({"checkType": "status_code"})
    info = {"username": "a", "parsing_enabled": False, "url_user": "https://x/a"}
    out = process_site_result(("<html/>", 404, None), Mock(), Mock(), info, site)
    assert out["status"].status == MaigretCheckStatus.AVAILABLE


def test_process_site_result_message_claimed():
    site = _make_site({
        "checkType": "message",
        "presenseStrs": ["profile-name"],
        "absenceStrs": ["not found"],
    })
    info = {"username": "a", "parsing_enabled": False, "url_user": "https://x/a"}
    out = process_site_result(("<div class='profile-name'>Alice</div>", 200, None), Mock(), Mock(), info, site)
    assert out["status"].status == MaigretCheckStatus.CLAIMED


def test_process_site_result_message_available_by_absence():
    site = _make_site({
        "checkType": "message",
        "presenseStrs": ["profile-name"],
        "absenceStrs": ["not found"],
    })
    info = {"username": "a", "parsing_enabled": False, "url_user": "https://x/a"}
    out = process_site_result(("<h1>not found</h1> profile-name too", 200, None), Mock(), Mock(), info, site)
    # absence marker wins even if presence marker also appears
    assert out["status"].status == MaigretCheckStatus.AVAILABLE


def test_process_site_result_with_error_is_unknown():
    site = _make_site({"checkType": "status_code"})
    info = {"username": "a", "parsing_enabled": False, "url_user": "https://x/a"}
    resp = ("body", 403, CheckError("Captcha", "Cloudflare"))
    out = process_site_result(resp, Mock(), Mock(), info, site)
    assert out["status"].status == MaigretCheckStatus.UNKNOWN
    assert out["status"].error is not None


def test_process_site_result_error_context_uses_instance():
    # Regression: context must render the CheckError instance, not the class.
    site = _make_site({"checkType": "status_code"})
    info = {"username": "a", "parsing_enabled": False, "url_user": "https://x/a"}
    err = CheckError("Request timeout", "slow server")
    out = process_site_result(("body", 0, err), Mock(), Mock(), info, site)
    assert out["status"].context == "Request timeout error: slow server"
    assert "class" not in out["status"].context


# ---- CurlCffiChecker: TLS impersonation header sanitisation ----


class _FakeCurlResponse:
    def __init__(self, text="ok", status_code=200):
        self.text = text
        self.status_code = status_code


class _FakeCurlSession:
    """Captures the kwargs of the last .get/.post/.head call for assertions."""

    last_method = None
    last_kwargs = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, **kwargs):
        type(self).last_method = 'get'
        type(self).last_kwargs = kwargs
        return _FakeCurlResponse()

    async def post(self, **kwargs):
        type(self).last_method = 'post'
        type(self).last_kwargs = kwargs
        return _FakeCurlResponse()

    async def head(self, **kwargs):
        type(self).last_method = 'head'
        type(self).last_kwargs = kwargs
        return _FakeCurlResponse()


@pytest.fixture
def fake_curl_cffi(monkeypatch):
    """Replace CurlCffiAsyncSession with a recorder. Resets capture between tests."""
    from maigret import checking
    _FakeCurlSession.last_method = None
    _FakeCurlSession.last_kwargs = None
    monkeypatch.setattr(checking, 'CurlCffiAsyncSession', _FakeCurlSession)
    return _FakeCurlSession


@pytest.mark.asyncio
async def test_curl_cffi_strips_random_user_agent_to_let_impersonation_drive_ua(fake_curl_cffi):
    """Regression: maigret used to forward `get_random_user_agent()` (often Chrome 91)
    to curl_cffi alongside `impersonate="chrome"` (Chrome 131 TLS). Cloudflare composite
    bot scoring rejects the resulting "Chrome 91 UA + Chrome 131 TLS" combo with a JS
    challenge. The fix strips User-Agent and Connection from the headers passed to
    curl_cffi so the impersonation default UA wins.
    """
    from maigret.checking import CurlCffiChecker

    checker = CurlCffiChecker(logger=Mock(), browser_emulate='chrome')
    checker.prepare(
        url='https://example.com/u/test',
        headers={
            "User-Agent": "Mozilla/5.0 ... Chrome/91.0.4472.124 ...",  # maigret default
            "Connection": "close",                                     # maigret default
        },
        allow_redirects=True,
        timeout=10,
        method='get',
    )
    await checker.check()

    sent = fake_curl_cffi.last_kwargs
    assert fake_curl_cffi.last_method == 'get'
    assert sent['impersonate'] == 'chrome'
    # The whole point of the fix: random UA must not leak through.
    assert sent['headers'] is None or 'User-Agent' not in sent['headers']
    assert sent['headers'] is None or 'user-agent' not in {k.lower() for k in sent['headers']}
    # Connection: close also stripped (interferes with impersonation defaults).
    assert sent['headers'] is None or 'Connection' not in sent['headers']


@pytest.mark.asyncio
async def test_curl_cffi_preserves_site_specific_headers(fake_curl_cffi):
    """Site-specific headers (e.g. Content-Type for POST APIs, auth tokens, cookies)
    must survive the User-Agent strip — only UA and Connection are removed.
    """
    from maigret.checking import CurlCffiChecker

    checker = CurlCffiChecker(logger=Mock(), browser_emulate='chrome')
    checker.prepare(
        url='https://example.com/api',
        headers={
            "User-Agent": "Mozilla/5.0 random",
            "Connection": "close",
            "Content-Type": "application/json",
            "X-Csrf-Token": "abc123",
        },
        allow_redirects=True,
        timeout=10,
        method='get',
    )
    await checker.check()

    sent_headers = fake_curl_cffi.last_kwargs['headers']
    assert sent_headers is not None
    assert sent_headers.get("Content-Type") == "application/json"
    assert sent_headers.get("X-Csrf-Token") == "abc123"
    # Sanity: stripped pair is gone
    assert "User-Agent" not in sent_headers
    assert "Connection" not in sent_headers


@pytest.mark.asyncio
async def test_curl_cffi_handles_empty_headers(fake_curl_cffi):
    """No headers at all → headers kwarg is None (not an empty dict that could confuse
    curl_cffi's impersonation header injection)."""
    from maigret.checking import CurlCffiChecker

    checker = CurlCffiChecker(logger=Mock(), browser_emulate='chrome')
    checker.prepare(
        url='https://example.com/u/test',
        headers=None,
        allow_redirects=True,
        timeout=10,
        method='get',
    )
    await checker.check()

    assert fake_curl_cffi.last_kwargs['headers'] is None
    assert fake_curl_cffi.last_kwargs['impersonate'] == 'chrome'


@pytest.mark.asyncio
async def test_curl_cffi_strips_ua_for_post_too(fake_curl_cffi):
    """The same UA-strip must apply on POST (e.g. Discord-style POST username probes
    with `tls_fingerprint`)."""
    from maigret.checking import CurlCffiChecker

    checker = CurlCffiChecker(logger=Mock(), browser_emulate='chrome')
    checker.prepare(
        url='https://example.com/api/check',
        headers={
            "User-Agent": "Mozilla/5.0 random",
            "Content-Type": "application/json",
        },
        allow_redirects=True,
        timeout=10,
        method='post',
        payload={"username": "test"},
    )
    await checker.check()

    sent = fake_curl_cffi.last_kwargs
    assert fake_curl_cffi.last_method == 'post'
    assert sent['json'] == {"username": "test"}
    assert "User-Agent" not in sent['headers']
    assert sent['headers'].get("Content-Type") == "application/json"
