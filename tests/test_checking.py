import asyncio
from argparse import ArgumentTypeError

from unittest.mock import Mock
import pytest

from maigret import search
from maigret.activation import ParsingActivator
from maigret.checking import (
    extract_ids_data,
    parse_usernames,
    update_results_info,
    get_failed_sites,
    timeout_check,
    debug_response_logging,
    process_site_result,
    check_site_for_username,
    run_url_mutations,
    _canonical_url,
    _domain_tail,
    MAX_MUTATIONS_PER_SITE,
    CheckerMock,
)
from maigret.error_detection import detect_error_page
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


def test_detect_error_page_instagram_login_wall():
    """Regression for #11: when Instagram serves the login wall (typically the
    response after rate-limiting an unauthenticated client), the JSON state
    contains `"routePath":"\\/"` (root path) rather than a username route. The
    Instagram entry in data.json carries this marker in `errors` so the result
    surfaces as UNKNOWN instead of a false AVAILABLE.
    """
    instagram_errors = {
        "Login • Instagram": "Login required",
        '"routePath":"\\/"': "Login required (rate-limited or session blocked)",
    }
    login_wall_html = '...{"routePath":"\\/"},"timeSpent":...'
    err = detect_error_page(login_wall_html, 200, instagram_errors, ignore_403=False)
    assert err is not None
    assert err.type == "Site-specific"
    assert "rate-limited" in err.desc


def test_detect_error_page_instagram_marker_no_false_positive_on_profile():
    """The login-wall marker must NOT match a real profile page. On a claimed
    user page, `routePath` carries the user-route template
    (`"routePath":"\\/{username}\\/..."`); the closing-quote form
    `"routePath":"\\/"` only appears on the login wall.
    """
    instagram_errors = {
        '"routePath":"\\/"': "Login required (rate-limited or session blocked)",
    }
    profile_html = (
        'foo,"routePath":"\\/{username}\\/{?tab}\\/{?view_type}\\/",bar'
    )
    err = detect_error_page(profile_html, 200, instagram_errors, ignore_403=False)
    assert err is None


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


def test_parse_usernames_rejects_url_value():
    """Regression for #1403: extractors sometimes return a URL under a *_username
    key; that URL must not be fed back as a candidate username."""
    logger = Mock()
    result = parse_usernames(
        {"instagram_username": "https://instagram.com/zuck"}, logger
    )
    assert result == {}


def test_parse_usernames_rejects_email_value():
    """Regression for #1403: e.g. socid_extractor's 'your_username' returns an
    email under a key matching the username heuristic."""
    logger = Mock()
    result = parse_usernames({"your_username": "alice@example.com"}, logger)
    assert result == {}


def test_parse_usernames_filters_urls_inside_list():
    logger = Mock()
    result = parse_usernames(
        {"other_usernames": "['alice', 'https://example.com/bob']"}, logger
    )
    # 'alice' should survive; the URL should be dropped.
    assert result == {"alice": "username"}


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


def test_process_site_result_message_non_ascii_username_no_match():
    """#2633: non-ASCII (e.g. Chinese) username with empty presenseStrs and
    response that doesn't contain the username → NOT claimed (avoid false positive)."""
    site = _make_site({
        "checkType": "message",
        "presenseStrs": [],
        "absenceStrs": [],
    })
    info = {"username": "快嘴摩卡酱", "parsing_enabled": False, "url_user": "https://x/%E5%BF%AB"}
    out = process_site_result(
        ("<html><title>Generic page</title><p>some content</p></html>", 200, None),
        Mock(), Mock(), info, site,
    )
    # Username not in response body → should NOT be CLAIMED
    assert out["status"].status != MaigretCheckStatus.CLAIMED


def test_process_site_result_message_non_ascii_username_with_match():
    """#2633: non-ASCII username that DOES appear in response → normal CLAIMED."""
    site = _make_site({
        "checkType": "message",
        "presenseStrs": [],
        "absenceStrs": [],
    })
    info = {"username": "快嘴摩卡酱", "parsing_enabled": False, "url_user": "https://x/%E5%BF%AB"}
    out = process_site_result(
        ("<html><title>快嘴摩卡酱的博客</title><p>欢迎来到快嘴摩卡酱的主页</p></html>", 200, None),
        Mock(), Mock(), info, site,
    )
    # Username IS in response → normal CLAIMED behavior (with empty presenseStrs)
    assert out["status"].status == MaigretCheckStatus.CLAIMED


def _process_default_site(site, body, status_code=200, username="random"):
    info = {
        "username": username,
        "parsing_enabled": False,
        "url_user": site.url.replace("{username}", username),
    }
    return process_site_result((body, status_code, None), Mock(), Mock(), info, site)


def test_hackernews_requires_profile_marker(default_db):
    site = default_db.sites_dict["HackerNews"]

    claimed = _process_default_site(
        site,
        '{"id":"blue","created":1270058024,"karma":1}',
        username="blue",
    )
    missing = _process_default_site(site, "null", username="random-hn-user")
    generic = _process_default_site(site, "Sorry.", username="random-hn-user")

    assert claimed["status"].status == MaigretCheckStatus.CLAIMED
    assert missing["status"].status == MaigretCheckStatus.AVAILABLE
    assert generic["status"].status == MaigretCheckStatus.AVAILABLE


def test_rajce_requires_profile_marker(default_db):
    site = default_db.sites_dict["Rajce.net"]

    claimed = _process_default_site(
        site,
        '<script>var settings = {"user":{"username":"blue"}}</script>',
        username="blue",
    )
    missing = _process_default_site(
        site,
        "<title>Uživatel neexistuje</title>",
        status_code=410,
        username="random-rajce-user",
    )
    generic = _process_default_site(
        site,
        "<html><title>Rajce.net</title></html>",
        username="random-rajce-user",
    )

    assert claimed["status"].status == MaigretCheckStatus.CLAIMED
    assert missing["status"].status == MaigretCheckStatus.AVAILABLE
    assert generic["status"].status == MaigretCheckStatus.AVAILABLE


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


@pytest.mark.asyncio
@pytest.mark.parametrize("protocol", ["tor", "i2p", "dns"])
async def test_check_site_for_username_skips_mock_protocol_checkers(protocol):
    site = _make_site({"protocol": protocol})

    class TrackingChecker(CheckerMock):
        checked = False

        async def check(self):
            self.checked = True
            return await super().check()

    checker = TrackingChecker()
    options = {
        "parsing": False,
        "cookie_jar": None,
        "forced": True,
        "id_type": "username",
        "timeout": 3,
        "proxy": None,
        "checkers": {protocol: checker},
    }
    query_notify = Mock()

    _, result = await check_site_for_username(
        site,
        "a",
        options,
        Mock(),
        query_notify,
    )

    status = result["status"]
    assert status.status == MaigretCheckStatus.ILLEGAL
    assert status.error.type == "Skipped"
    assert status.error.desc == f"no {protocol} gateway configured"
    assert "Connection lost" not in str(status.error)
    assert checker.checked is False
    query_notify.update.assert_called_once_with(status, site.similar_search)


@pytest.mark.asyncio
async def test_check_site_for_username_preserves_clearweb_connection_lost():
    site = _make_site()

    class FailingChecker:
        prepared = False
        checked = False

        def prepare(self, *args, **kwargs):
            self.prepared = True
            return None

        async def check(self):
            self.checked = True
            return "", 0, CheckError("Connection lost")

    checker = FailingChecker()
    options = {
        "parsing": False,
        "cookie_jar": None,
        "forced": True,
        "id_type": "username",
        "timeout": 3,
        "proxy": None,
        "checkers": {"": checker},
    }

    _, result = await check_site_for_username(
        site,
        "a",
        options,
        Mock(),
        Mock(),
    )

    assert checker.prepared is True
    assert checker.checked is True
    assert result["status"].status == MaigretCheckStatus.UNKNOWN
    assert result["status"].error.type == "Connection lost"


@pytest.mark.asyncio
async def test_check_site_for_username_awaits_activation_before_retry(monkeypatch):
    site = _make_site({
        "checkType": "status_code",
        "headers": {"X-Initial": "1"},
        "activation": {
            "method": "test_async",
            "marks": ["NEEDS_ACTIVATION"],
        },
        "protocol": "https",
    })

    class FakeChecker:
        def __init__(self):
            self.calls = 0
            self.prepared_headers = []
            self.url = None
            self.headers = None
            self.allow_redirects = True
            self.timeout = 0
            self.method = "get"
            self.payload = None

        def prepare(
            self,
            url,
            headers=None,
            allow_redirects=True,
            timeout=0,
            method="get",
            payload=None,
        ):
            self.url = url
            self.headers = headers
            self.allow_redirects = allow_redirects
            self.timeout = timeout
            self.method = method
            self.payload = payload
            self.prepared_headers.append(dict(headers or {}))
            return None

        async def check(self):
            self.calls += 1
            if self.calls == 1:
                return "NEEDS_ACTIVATION", 200, None
            return "activated", 200, None

    async def activate(site, logger, **kwargs):
        await asyncio.sleep(0)
        site.headers["X-Activated"] = "yes"

    checker = FakeChecker()
    monkeypatch.setattr(
        ParsingActivator,
        "test_async",
        staticmethod(activate),
        raising=False,
    )

    options = {
        "parsing": False,
        "cookie_jar": None,
        "forced": True,
        "id_type": "username",
        "timeout": 3,
        "proxy": None,
        "checkers": {"https": checker},
    }

    _, result = await check_site_for_username(
        site,
        "a",
        options,
        Mock(),
        Mock(),
    )

    assert checker.calls == 2
    assert checker.prepared_headers[-1]["X-Activated"] == "yes"
    assert result["status"].status == MaigretCheckStatus.CLAIMED


@pytest.mark.asyncio
async def test_concurrent_activation_uses_independent_checkers(monkeypatch):
    instances = []

    class FakeChecker:
        def __init__(self):
            self.calls = 0
            self.prepared_urls = []
            self.url = None
            self.headers = None
            self.allow_redirects = True
            self.timeout = 0
            self.method = "get"
            self.payload = None
            instances.append(self)

        def prepare(
            self,
            url,
            headers=None,
            allow_redirects=True,
            timeout=0,
            method="get",
            payload=None,
        ):
            self.url = url
            self.headers = headers
            self.allow_redirects = allow_redirects
            self.timeout = timeout
            self.method = method
            self.payload = payload
            self.prepared_urls.append(url)
            return None

        async def check(self):
            await asyncio.sleep(0)
            self.calls += 1
            if self.calls == 1:
                return "NEEDS_ACTIVATION", 200, None
            return "activated", 200, None

    async def activate(site, logger, **kwargs):
        await asyncio.sleep(0)
        site.headers["X-Activated"] = site.name

    monkeypatch.setattr(
        ParsingActivator,
        "test_async",
        staticmethod(activate),
        raising=False,
    )

    options = {
        "parsing": False,
        "cookie_jar": None,
        "forced": True,
        "id_type": "username",
        "timeout": 3,
        "proxy": None,
        "checkers": {"https": FakeChecker},
    }
    first = _make_site({
        "url": "https://x/one/{username}",
        "urlMain": "https://x",
        "checkType": "status_code",
        "activation": {"method": "test_async", "marks": ["NEEDS_ACTIVATION"]},
        "protocol": "https",
    })
    first.name = "First"
    second = _make_site({
        "url": "https://x/two/{username}",
        "urlMain": "https://x",
        "checkType": "status_code",
        "activation": {"method": "test_async", "marks": ["NEEDS_ACTIVATION"]},
        "protocol": "https",
    })
    second.name = "Second"

    await asyncio.gather(
        check_site_for_username(first, "a", options, Mock(), Mock()),
        check_site_for_username(second, "a", options, Mock(), Mock()),
    )

    assert len(instances) == 2
    assert [checker.prepared_urls for checker in instances] == [
        ["https://x/one/a", "https://x/one/a"],
        ["https://x/two/a", "https://x/two/a"],
    ]


# ---- CurlCffiChecker: TLS impersonation header sanitisation ----


class _FakeCurlResponse:
    def __init__(self, text="ok", status_code=200):
        self.text = text
        self.status_code = status_code


class _FakeCurlSession:
    """Captures constructor + .get/.post/.head call kwargs for assertions."""

    last_method = None
    last_kwargs = None
    last_init_kwargs = None

    def __init__(self, **kwargs):
        type(self).last_init_kwargs = kwargs

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
    _FakeCurlSession.last_init_kwargs = None
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


@pytest.mark.asyncio
async def test_curl_cffi_forwards_proxy_to_async_session(fake_curl_cffi):
    """Regression for #2648: when --proxy is set, the proxy URL must be
    forwarded to curl_cffi's AsyncSession via the `proxies` kwarg on the
    session constructor. Otherwise sites with `tls_fingerprint` protection
    (Instagram, Reddit, SoundCloud, Threads, …) silently bypass the
    configured proxy and connect direct.
    """
    from maigret.checking import CurlCffiChecker

    proxy = "http://user:pass@proxy.example.com:8080"
    checker = CurlCffiChecker(logger=Mock(), browser_emulate='chrome', proxy=proxy)
    checker.prepare(
        url='https://example.com/u/test',
        headers=None,
        allow_redirects=True,
        timeout=10,
        method='get',
    )
    await checker.check()

    init = fake_curl_cffi.last_init_kwargs
    assert init is not None, "CurlCffiAsyncSession was never constructed"
    # curl_cffi expects the standard requests-style {scheme: url} mapping
    assert init.get('proxies') == {'http': proxy, 'https': proxy}


@pytest.mark.asyncio
async def test_curl_cffi_no_proxy_omits_proxies_kwarg(fake_curl_cffi):
    """Counterpart to the proxy-forwarding test: when no proxy is configured,
    the `proxies` kwarg must NOT appear on the AsyncSession constructor.
    Passing `proxies=None` or an empty mapping would let curl_cffi inherit
    the process-wide HTTPS_PROXY env var unintentionally.
    """
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

    init = fake_curl_cffi.last_init_kwargs
    assert init is not None, "CurlCffiAsyncSession was never constructed"
    assert 'proxies' not in init


# -----------------------------------------------------------------------------
# DNS-resolver selection (issue #2688). When --dns-resolver=threaded is passed,
# SimpleAiohttpChecker must build the TCPConnector with an explicit
# ThreadedResolver instead of letting aiohttp default to AsyncResolver
# (aiodns/c-ares), which fails on Windows / VPN / corporate networks with
# "Could not contact DNS servers".
# -----------------------------------------------------------------------------


def _capture_tcpconnector(monkeypatch):
    """Replace aiohttp.TCPConnector with a constructor-recorder. Each call
    appends its kwargs to the returned list. ClientSession will then receive
    a never-used dummy connector — we don't actually want to open sockets in
    tests."""
    from maigret import checking
    captured = []

    class _DummyConnector:
        def __init__(self, *args, **kwargs):
            captured.append(kwargs)
            # aiohttp's ClientSession expects these on its connector
            self._loop = None
            self.closed = False
        async def close(self):
            pass
        @property
        def force_close(self):
            return False

    monkeypatch.setattr(checking, 'TCPConnector', _DummyConnector)
    return captured


@pytest.mark.asyncio
async def test_dns_resolver_threaded_passes_threaded_resolver_to_tcpconnector(monkeypatch):
    """Issue #2688: with dns_resolver='threaded', the connector must be built
    with a ThreadedResolver so DNS resolution goes through the OS, not aiodns."""
    from maigret.checking import SimpleAiohttpChecker
    from aiohttp.resolver import ThreadedResolver

    captured = _capture_tcpconnector(monkeypatch)

    checker = SimpleAiohttpChecker(logger=Mock(), dns_resolver='threaded')
    checker.prepare(url='https://example.com/u/test')
    # The ClientSession context manager will try to use _DummyConnector and
    # then make an HTTP request — we don't care about the request itself,
    # only about the TCPConnector kwargs that were captured before any I/O.
    try:
        await checker.check()
    except Exception:
        pass

    assert captured, "TCPConnector was never constructed — check() bailed out earlier"
    init_kwargs = captured[0]
    assert 'resolver' in init_kwargs, "dns_resolver='threaded' did not forward a resolver to TCPConnector"
    assert isinstance(init_kwargs['resolver'], ThreadedResolver)


@pytest.mark.asyncio
async def test_dns_resolver_async_omits_resolver_kwarg(monkeypatch):
    """Default ('async') must NOT pass an explicit resolver, so aiohttp uses
    its DefaultResolver (AsyncResolver via aiodns). Passing resolver=None
    would override the smart default with an invalid value."""
    from maigret.checking import SimpleAiohttpChecker

    captured = _capture_tcpconnector(monkeypatch)

    checker = SimpleAiohttpChecker(logger=Mock())  # default
    checker.prepare(url='https://example.com/u/test')
    try:
        await checker.check()
    except Exception:
        pass

    assert captured
    init_kwargs = captured[0]
    assert 'resolver' not in init_kwargs, (
        "Default dns_resolver='async' must not pass a resolver kwarg — let "
        "aiohttp pick DefaultResolver"
    )


# -----------------------------------------------------------------------------
# cookie_jar forwarding (issue #2666). SimpleAiohttpChecker.check() builds the
# ClientSession with `cookie_jar=self.cookie_jar if self.cookie_jar else None`,
# but the path was flagged `# TODO: tests` because nothing asserted the jar
# passed to the checker actually reached the outgoing ClientSession.
# -----------------------------------------------------------------------------


def _capture_clientsession(monkeypatch):
    """Replace aiohttp.ClientSession with a constructor-recorder so we can
    assert on the kwargs it received (cookie_jar in particular) without
    opening any sockets. Mirrors the _capture_tcpconnector pattern above."""
    from maigret import checking
    captured = []

    class _DummySession:
        def __init__(self, *args, **kwargs):
            captured.append(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def close(self):
            pass

    monkeypatch.setattr(checking, 'ClientSession', _DummySession)
    return captured


@pytest.mark.asyncio
async def test_cookie_jar_forwarded_to_clientsession(monkeypatch):
    """Issue #2666: the cookie_jar passed to SimpleAiohttpChecker must reach
    ClientSession(cookie_jar=...) on the outgoing request. Reuses the
    constructor-capture pattern from the DNS-resolver tests above.

    A sentinel object stands in for the real aiohttp.CookieJar: check() only
    does `self.cookie_jar if self.cookie_jar else None`, so any truthy object
    proves the forwarding. Avoiding CookieJar() also sidesteps its event-loop
    requirement under pytest-asyncio, keeping this a pure unit test."""
    from maigret.checking import SimpleAiohttpChecker

    captured = _capture_clientsession(monkeypatch)
    _capture_tcpconnector(monkeypatch)  # keep check() from opening a socket

    sentinel_jar = object()  # any truthy stand-in for the CookieJar
    checker = SimpleAiohttpChecker(logger=Mock(), cookie_jar=sentinel_jar)
    checker.prepare(url='https://example.com/u/test')
    try:
        await checker.check()
    except Exception:
        pass

    assert captured, "ClientSession was never constructed — check() bailed out earlier"
    init_kwargs = captured[0]
    assert init_kwargs.get('cookie_jar') is sentinel_jar, (
        "cookie_jar passed to SimpleAiohttpChecker was not forwarded to ClientSession"
    )


@pytest.mark.asyncio
async def test_no_cookie_jar_passes_none_to_clientsession(monkeypatch):
    """Counterpart to the above: with no cookie_jar configured, ClientSession
    must receive `cookie_jar=None` (the `else None` branch), not the default
    aiohttp CookieJar — maigret manages cookie persistence explicitly via
    import_aiohttp_cookies and must not let aiohttp silently persist cookies."""
    from maigret.checking import SimpleAiohttpChecker

    captured = _capture_clientsession(monkeypatch)
    _capture_tcpconnector(monkeypatch)

    checker = SimpleAiohttpChecker(logger=Mock())  # no cookie_jar
    checker.prepare(url='https://example.com/u/test')
    try:
        await checker.check()
    except Exception:
        pass

    assert captured, "ClientSession was never constructed — check() bailed out earlier"
    init_kwargs = captured[0]
    assert init_kwargs.get('cookie_jar') is None, (
        "No cookie_jar configured, but ClientSession received a non-None cookie_jar"
    )


# -- --enrich / url_mutations --------------------------------------------------


def test_canonical_url_ignores_query_and_trailing_slash():
    """(scheme, host, path) tuple is what dedup compares."""
    a = _canonical_url("https://leetcode.com/graphql/")
    b = _canonical_url("https://leetcode.com/graphql?query=abc&variables=xyz")
    assert a == b


def test_canonical_url_lowercases_scheme_and_host():
    assert _canonical_url("HTTPS://API.Example.COM/u/A") == _canonical_url(
        "https://api.example.com/u/A"
    )


def test_canonical_url_distinguishes_different_paths():
    assert _canonical_url("https://x.com/a") != _canonical_url("https://x.com/b")


def test_canonical_url_handles_empty():
    assert _canonical_url("") == ("", "", "")


def test_domain_tail_two_labels_or_deep_subdomain():
    assert _domain_tail("github.com") == "github.com"
    assert _domain_tail("api.github.com") == "github.com"
    assert _domain_tail("a.b.c.example.com") == "example.com"


def test_domain_tail_degenerate():
    assert _domain_tail("localhost") == "localhost"
    assert _domain_tail("") == ""


class _MutationChecker(CheckerMock):
    """Checker that hands out canned responses in order and records URLs seen."""

    def __init__(self, responses):
        super().__init__()
        self._responses = list(responses)
        self.urls_seen = []
        self.headers = {}
        self.timeout = 3

    def prepare(self, url, headers=None, allow_redirects=True, timeout=0, method='get', payload=None):
        self.urls_seen.append(url)
        self.headers = headers or {}
        self.timeout = timeout or self.timeout
        return None

    async def check(self):
        if not self._responses:
            return '', 0, None
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_run_url_mutations_merges_extracted_fields(monkeypatch):
    """A mutation URL fetch → extract → merge into ids_data / ids_usernames / ids_links."""
    from maigret import checking as checking_mod

    site = _make_site()
    checker = _MutationChecker([("api-body", 200, None)])
    result = MaigretCheckResult("alice", "TestSite", "https://x/alice", MaigretCheckStatus.CLAIMED)
    result.ids_data = {"bio": "from base page"}
    results_info = {
        "status": result,
        "url_user": "https://x/alice",
        "ids_usernames": {"alice_base": "username"},
        "ids_links": ["https://base.example/link"],
    }

    monkeypatch.setattr(
        checking_mod,
        "mutate_url",
        lambda url: [("https://api.example.com/u/alice", {"X-Api": "1"})],
    )
    monkeypatch.setattr(
        checking_mod,
        "extract",
        lambda html: {
            "uid": "42",
            "fullname": "Alice",
            "bio": "from mutation (should NOT overwrite)",
            "linked_username": "alice_alt",
            "links": "['https://mut.example/a']",
            "website": "https://alice.example",
        },
    )

    await run_url_mutations(
        checker=checker,
        site=site,
        results_info=results_info,
        options={"enrich": True},
        logger=Mock(),
    )

    # mutation URL was hit with merged headers
    assert checker.urls_seen == ["https://api.example.com/u/alice"]
    assert checker.headers.get("X-Api") == "1"

    # new fields land in ids_data, but base-page fields survive
    assert result.ids_data["uid"] == "42"
    assert result.ids_data["fullname"] == "Alice"
    assert result.ids_data["bio"] == "from base page"

    # ids_usernames / ids_links merge, base values preserved
    assert results_info["ids_usernames"] == {
        "alice_base": "username",
        "alice_alt": "username",
    }
    assert "https://base.example/link" in results_info["ids_links"]
    assert "https://mut.example/a" in results_info["ids_links"]
    assert "https://alice.example" in results_info["ids_links"]


@pytest.mark.asyncio
async def test_run_url_mutations_merge_is_silent_by_default(monkeypatch):
    """A successful merge does NOT emit its own enrich line — the new fields
    show up in the [+] Site: block's tree once run_url_mutations returns
    (it runs BEFORE query_notify.update). Only diagnostics fire, and those
    are verbose-only."""
    from maigret import checking as checking_mod

    checker = _MutationChecker([("body", 200, None)])
    result = MaigretCheckResult("a", "TestSite", "https://x/a", MaigretCheckStatus.CLAIMED)
    result.ids_data = {}
    results_info = {"status": result, "url_user": "https://x/a"}

    monkeypatch.setattr(
        checking_mod, "mutate_url", lambda url: [("https://api.example/u/a", {})]
    )
    monkeypatch.setattr(checking_mod, "extract", lambda html: {"uid": "1"})

    notify = Mock()
    notify.verbose = False
    await run_url_mutations(
        checker=checker, site=_make_site(), results_info=results_info,
        options={"enrich": True}, logger=Mock(), query_notify=notify,
    )
    # new field landed in ids_data — it will render inside the site tree
    assert result.ids_data.get("uid") == "1"
    # no per-merge notification line — the tree IS the notification
    non_verbose = [
        c for c in notify.enrich.call_args_list
        if c.kwargs.get("verbose_only") is not True
    ]
    assert non_verbose == []


@pytest.mark.asyncio
async def test_run_url_mutations_marks_no_data_paths_verbose_only(monkeypatch):
    """No-new-data outcomes (collision, no-scheme, empty body) are all verbose-only."""
    from maigret import checking as checking_mod

    checker = _MutationChecker([
        ("body-1", 200, None),   # extract matches but nothing new
        ("body-2", 200, None),   # extract returns {} — no scheme matched
        ("", 404, None),         # empty body
    ])
    result = MaigretCheckResult("a", "S", "https://x/a", MaigretCheckStatus.CLAIMED)
    result.ids_data = {"uid": "already-known"}
    results_info = {"status": result, "url_user": "https://x/a"}

    monkeypatch.setattr(
        checking_mod, "mutate_url",
        lambda url: [
            ("https://a.example/1", {}),
            ("https://a.example/2", {}),
            ("https://a.example/3", {}),
        ],
    )
    extract_results = iter([{"uid": "already-known"}, {}, {}])
    monkeypatch.setattr(checking_mod, "extract", lambda html: next(extract_results))

    notify = Mock()
    notify.verbose = False
    await run_url_mutations(
        checker=checker, site=_make_site(), results_info=results_info,
        options={"enrich": True}, logger=Mock(), query_notify=notify,
    )
    # All 3 non-discovery events flagged verbose_only=True so the real
    # notifier would swallow them in default mode.
    assert notify.enrich.call_count == 3
    for c in notify.enrich.call_args_list:
        assert c.kwargs.get("verbose_only") is True
    msgs = [c.args[0] for c in notify.enrich.call_args_list]
    assert any("no new data" in m for m in msgs)
    assert any("no socid_extractor scheme matched" in m for m in msgs)
    assert any("empty body" in m for m in msgs)
    assert not any("merged +0f" in m for m in msgs)


@pytest.mark.asyncio
async def test_run_url_mutations_skips_cross_site(monkeypatch):
    """A mutation whose domain differs from the site's url_main must be dropped."""
    from maigret import checking as checking_mod

    checker = _MutationChecker([("body", 200, None)])
    result = MaigretCheckResult("a", "S", "https://archive.org/x", MaigretCheckStatus.CLAIMED)
    result.ids_data = {}
    results_info = {
        "status": result,
        "url_user": "https://archive.org/wayback/available?url=https://twitter.com/a",
    }

    monkeypatch.setattr(
        checking_mod, "mutate_url",
        lambda url: [
            ("https://twitter.com/i/api/graphql/...", set()),          # foreign — drop
            ("https://web.archive.org/wayback/api/...", set()),         # same eTLD+1 — keep
        ],
    )
    monkeypatch.setattr(checking_mod, "extract", lambda html: {})

    notify = Mock()
    notify.verbose = False
    await run_url_mutations(
        checker=checker,
        site=_make_site({"urlMain": "https://archive.org"}),
        results_info=results_info,
        options={"enrich": True},
        logger=Mock(),
        query_notify=notify,
    )
    assert checker.urls_seen == ["https://web.archive.org/wayback/api/..."]
    skip_calls = [c for c in notify.enrich.call_args_list if "cross-site" in c.args[0]]
    assert len(skip_calls) == 1
    assert skip_calls[0].kwargs.get("verbose_only") is True


@pytest.mark.asyncio
async def test_run_url_mutations_drops_body_headers(monkeypatch):
    """Content-Type / Content-Length from the base POST must not leak into a GET
    mutation — LeetCode GraphQL 400s on a body-less GET with application/json."""
    from maigret import checking as checking_mod

    checker = _MutationChecker([("body", 200, None)])
    # simulate a POST-based base check whose checker.headers carry Content-Type
    checker.headers = {"User-Agent": "UA", "Content-Type": "application/json"}
    result = MaigretCheckResult("a", "S", "https://x/a", MaigretCheckStatus.CLAIMED)
    result.ids_data = {}
    results_info = {"status": result, "url_user": "https://x/a"}

    monkeypatch.setattr(
        checking_mod, "mutate_url", lambda url: [("https://api.example/gql", {})],
    )
    monkeypatch.setattr(checking_mod, "extract", lambda html: {})

    await run_url_mutations(
        checker=checker, site=_make_site({"headers": {"Content-Type": "application/json"}}),
        results_info=results_info, options={"enrich": True}, logger=Mock(),
    )
    assert "Content-Type" not in checker.headers
    assert "Content-Length" not in checker.headers
    assert checker.headers.get("User-Agent") == "UA"


@pytest.mark.asyncio
async def test_run_url_mutations_skips_url_probe_duplicate(monkeypatch):
    """A mutation URL equal to the site's already-fetched url_probe must be skipped."""
    from maigret import checking as checking_mod

    checker = _MutationChecker([("body", 200, None)])
    result = MaigretCheckResult("a", "S", "https://x/a", MaigretCheckStatus.CLAIMED)
    result.ids_data = {}
    results_info = {
        "status": result,
        "url_user": "https://x/a",
        "url_probe": "https://api.example/u/a",
    }

    monkeypatch.setattr(
        checking_mod, "mutate_url",
        lambda url: [
            # scheme+host+path match url_probe (differ only in query/trailing slash) — drop
            ("https://api.example/u/a/?q=1", {}),
            ("https://other.example/u/a", {}),  # keep
        ],
    )
    monkeypatch.setattr(checking_mod, "extract", lambda html: {})

    notify = Mock()
    notify.verbose = False
    await run_url_mutations(
        checker=checker, site=_make_site(), results_info=results_info,
        options={"enrich": True}, logger=Mock(), query_notify=notify,
    )
    # only the non-duplicate URL was fetched
    assert checker.urls_seen == ["https://other.example/u/a"]
    # skip message is emitted with the new wording, verbose-only
    skip_calls = [c for c in notify.enrich.call_args_list if "skip" in c.args[0]]
    assert len(skip_calls) == 1
    assert "maigret has built-in check for this mutation" in skip_calls[0].args[0]
    assert skip_calls[0].kwargs.get("verbose_only") is True


@pytest.mark.asyncio
async def test_run_url_mutations_empty_mutations_is_noop(monkeypatch):
    from maigret import checking as checking_mod

    checker = _MutationChecker([])
    result = MaigretCheckResult("a", "S", "https://x/a", MaigretCheckStatus.CLAIMED)
    results_info = {"status": result, "url_user": "https://x/a"}

    monkeypatch.setattr(checking_mod, "mutate_url", lambda url: [])
    # extract must never be called
    monkeypatch.setattr(
        checking_mod, "extract", lambda html: (_ for _ in ()).throw(AssertionError("should not run"))
    )

    await run_url_mutations(
        checker=checker, site=_make_site(), results_info=results_info,
        options={"enrich": True}, logger=Mock(),
    )
    assert checker.urls_seen == []


@pytest.mark.asyncio
async def test_run_url_mutations_caps_at_max(monkeypatch):
    from maigret import checking as checking_mod

    n = MAX_MUTATIONS_PER_SITE + 5
    checker = _MutationChecker([("body", 200, None)] * n)
    result = MaigretCheckResult("a", "S", "https://x/a", MaigretCheckStatus.CLAIMED)
    result.ids_data = {}
    results_info = {"status": result, "url_user": "https://x/a"}

    monkeypatch.setattr(
        checking_mod, "mutate_url",
        lambda url: [(f"https://m{i}.example/a", {}) for i in range(n)],
    )
    monkeypatch.setattr(checking_mod, "extract", lambda html: {})

    options = {"enrich": True, "enrich_requests": 0}
    await run_url_mutations(
        checker=checker, site=_make_site(), results_info=results_info,
        options=options, logger=Mock(),
    )
    assert len(checker.urls_seen) == MAX_MUTATIONS_PER_SITE
    # counter tracks attempted requests
    assert options["enrich_requests"] == MAX_MUTATIONS_PER_SITE


@pytest.mark.asyncio
async def test_run_url_mutations_swallows_checker_exception(monkeypatch):
    """A crashing mutation request must not sink the primary CLAIMED result."""
    from maigret import checking as checking_mod

    class ExplodingChecker(_MutationChecker):
        async def check(self):
            raise RuntimeError("network is on fire")

    checker = ExplodingChecker([])
    result = MaigretCheckResult("a", "S", "https://x/a", MaigretCheckStatus.CLAIMED)
    result.ids_data = {"bio": "kept"}
    results_info = {"status": result, "url_user": "https://x/a"}

    monkeypatch.setattr(
        checking_mod, "mutate_url",
        lambda url: [("https://m.example/a", {})],
    )
    monkeypatch.setattr(checking_mod, "extract", lambda html: {"uid": "must-not-be-added"})

    logger = Mock()
    await run_url_mutations(
        checker=checker, site=_make_site(), results_info=results_info,
        options={"enrich": True}, logger=logger,
    )

    # primary result intact; nothing partial injected
    assert result.ids_data == {"bio": "kept"}
    logger.warning.assert_called()


@pytest.mark.asyncio
async def test_enrich_disabled_skips_mutations(monkeypatch):
    """Without options['enrich'], check_site_for_username must not call mutate_url."""
    from maigret import checking as checking_mod

    called = {"n": 0}

    def spy_mutate(url):
        called["n"] += 1
        return []

    monkeypatch.setattr(checking_mod, "mutate_url", spy_mutate)

    site = _make_site()
    options = {
        "parsing": False,
        "enrich": False,
        "cookie_jar": None,
        "forced": False,
        "id_type": "username",
        "timeout": 3,
        "proxy": None,
        "checkers": {"": CheckerMock()},
    }
    await check_site_for_username(site, "a", options, Mock(), Mock())
    assert called["n"] == 0
