"""Maigret activation test functions"""

import inspect
import json
import os
import sys

import yarl

import aiohttp
import pytest
from unittest.mock import Mock

from tests.conftest import LOCAL_SERVER_PORT
from maigret import activation as activation_cache
from maigret.activation import (
    ParsingActivator,
    import_aiohttp_cookies,
    load_activation_cache,
    save_activation_cache,
)
from maigret.sites import MaigretDatabase, MaigretSite

COOKIES_TXT = """# HTTP Cookie File downloaded with cookies.txt by Genuinous @genuinous
# This file can be used by wget, curl, aria2c and other standard compliant tools.
# Usage Examples:
#   1) wget -x --load-cookies cookies.txt "https://xss.is/search/"
#   2) curl --cookie cookies.txt "https://xss.is/search/"
#   3) aria2c --load-cookies cookies.txt "https://xss.is/search/"
#
xss.is	FALSE	/	TRUE	0	xf_csrf	test
xss.is	FALSE	/	TRUE	1642709308	xf_user	tset
.xss.is	TRUE	/	FALSE	0	muchacho_cache	test
.xss.is	TRUE	/	FALSE	1924905600	132_evc	test
localhost	FALSE	/	FALSE	0	a	b
"""


@pytest.mark.skip("captcha")
@pytest.mark.slow
@pytest.mark.asyncio
async def test_vimeo_activation(default_db):
    vimeo_site = default_db.sites_dict['Vimeo']
    token1 = vimeo_site.headers['Authorization']

    await ParsingActivator.vimeo(vimeo_site, Mock())
    token2 = vimeo_site.headers['Authorization']

    assert token1 != token2


@pytest.mark.slow
@pytest.mark.asyncio
async def test_import_aiohttp_cookies(cookie_test_server):
    cookies_filename = 'cookies_test.txt'
    with open(cookies_filename, 'w') as f:
        f.write(COOKIES_TXT)

    cookie_jar = import_aiohttp_cookies(cookies_filename)
    url = f'http://localhost:{LOCAL_SERVER_PORT}/cookies'

    cookies = cookie_jar.filter_cookies(yarl.URL(url))
    assert cookies['a'].value == 'b'

    async with aiohttp.ClientSession(cookie_jar=cookie_jar) as session:
        async with session.get(url=url) as response:
            result = await response.json()
            print(f"Server response: {result}")

    assert result == {'cookies': {'a': 'b'}}


# A real browser export usually stores several cookies per domain under
# different paths. COOKIES_TXT above happens to keep everything on "/", which
# is why the path handling below went untested for so long.
MULTIPATH_COOKIES_TXT = """# Netscape HTTP Cookie File
.example.com	TRUE	/	FALSE	2147483647	sessionid	SESSION
.example.com	TRUE	/account	FALSE	2147483647	csrftoken	CSRF
.example.com	TRUE	/api	FALSE	2147483647	authtoken	AUTH
"""

# A cookie stored with no value at all: the name column is empty and the value
# column carries the name, which http.cookiejar parses as value None.
VALUELESS_COOKIE_TXT = """# Netscape HTTP Cookie File
.example.com	TRUE	/	FALSE	2147483647		consent
"""


def _write(tmp_path, content):
    cookies_file = tmp_path / "cookies.txt"
    cookies_file.write_text(content, encoding="utf-8")
    return str(cookies_file)


@pytest.mark.asyncio
async def test_import_aiohttp_cookies_keeps_every_path_of_a_domain(tmp_path):
    """All of a domain's cookies must survive the import, not just one path.

    MozillaCookieJar stores cookies as {domain: {path: {name: cookie}}}. Taking
    a single path bucket per domain silently discarded every cookie saved under
    the domain's other paths, so an authenticated scan went out missing its CSRF
    and auth tokens and simply looked logged out.
    """
    cookie_jar = import_aiohttp_cookies(_write(tmp_path, MULTIPATH_COOKIES_TXT))

    imported = {morsel.key for morsel in cookie_jar}
    assert imported == {"sessionid", "csrftoken", "authtoken"}


@pytest.mark.asyncio
async def test_import_aiohttp_cookies_offers_each_cookie_on_its_own_path(tmp_path):
    """Path scoping still has to hold once every cookie is imported."""
    cookie_jar = import_aiohttp_cookies(_write(tmp_path, MULTIPATH_COOKIES_TXT))

    def sent_to(url):
        return {
            key: morsel.value
            for key, morsel in cookie_jar.filter_cookies(yarl.URL(url)).items()
        }

    assert sent_to("http://www.example.com/") == {"sessionid": "SESSION"}
    assert sent_to("http://www.example.com/account/profile") == {
        "sessionid": "SESSION",
        "csrftoken": "CSRF",
    }
    assert sent_to("http://www.example.com/api/v1/users") == {
        "sessionid": "SESSION",
        "authtoken": "AUTH",
    }


@pytest.mark.asyncio
async def test_import_aiohttp_cookies_does_not_invent_a_none_value(tmp_path):
    """A valueless cookie must not reach the wire as the literal text 'None'."""
    cookie_jar = import_aiohttp_cookies(_write(tmp_path, VALUELESS_COOKIE_TXT))

    sent = cookie_jar.filter_cookies(yarl.URL("http://www.example.com/"))
    assert sent["consent"].value == ""


# ---- OnlyFans signing tests (pure-compute, no network) ----


class _FakeSite:
    """Minimal stand-in for MaigretSite with the attributes onlyfans() touches."""

    def __init__(self, headers=None, activation=None):
        self.headers = headers or {}
        self.activation = activation or {
            "static_param": "jLM8LXHU1CGcuCzPMNwWX9osCScVuP4D",
            "checksum_indexes": [28, 3, 16, 32, 25, 24, 23, 0, 26],
            "checksum_constant": -180,
            "format": "57203:{}:{:x}:69cfa6d8",
            "url": "https://onlyfans.com/api2/v2/init",
        }


class _FakeResponse:
    def __init__(self, cookies=None, json_data=None):
        self.cookies = {
            key: type("Cookie", (), {"value": value})()
            for key, value in (cookies or {}).items()
        }
        self._json_data = json_data or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self, content_type=None):
        return self._json_data


@pytest.mark.parametrize("method", ["twitter", "vimeo", "onlyfans", "weibo", "proton"])
def test_activation_methods_are_coroutines(method):
    assert inspect.iscoroutinefunction(getattr(ParsingActivator, method))


@pytest.mark.asyncio
async def test_vimeo_activation_uses_aiohttp(monkeypatch):
    site = _FakeSite(
        headers={"Authorization": "old-token", "User-Agent": "test"},
        activation={"url": "https://vimeo.test/viewer"},
    )
    captured = {}

    class FakeSession:
        def __init__(self, **kwargs):
            captured["session_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, url, headers=None, timeout=None):
            captured["url"] = url
            captured["headers"] = dict(headers or {})
            captured["timeout"] = timeout
            return _FakeResponse(json_data={"jwt": "fresh"})

    monkeypatch.setattr("maigret.activation.ClientSession", FakeSession)

    await ParsingActivator.vimeo(site, Mock(), timeout=7)

    assert captured["url"] == "https://vimeo.test/viewer"
    assert captured["headers"] == {"User-Agent": "test"}
    assert captured["timeout"] == 7
    assert captured["session_kwargs"] == {"trust_env": True}
    assert site.headers["Authorization"] == "jwt fresh"


@pytest.mark.asyncio
async def test_onlyfans_sets_xbc_when_zero(monkeypatch):
    site = _FakeSite(headers={"x-bc": "0", "cookie": "existing=1"})

    # Prevent any real network. If _sign path still opens a session, fail loudly.
    def boom(*a, **kw):  # pragma: no cover - sanity
        raise AssertionError("ClientSession should not open when cookie is present")

    monkeypatch.setattr("maigret.activation.ClientSession", boom)

    logger = Mock()
    await ParsingActivator.onlyfans(
        site,
        logger,
        url="https://onlyfans.com/api2/v2/users/adam",
    )

    # x-bc must be rewritten to a non-zero hex token
    assert site.headers["x-bc"] != "0"
    assert len(site.headers["x-bc"]) == 40  # 20 bytes → 40 hex chars
    # time / sign headers set for target URL
    assert "time" in site.headers and site.headers["time"].isdigit()
    assert site.headers["sign"].startswith("57203:")


@pytest.mark.asyncio
async def test_onlyfans_fetches_init_cookie_when_missing(monkeypatch):
    """When cookie header is absent, init endpoint is called and its cookies stored."""
    site = _FakeSite(headers={"x-bc": "already_set_token", "user-id": "0"})

    captured = {}

    class FakeSession:
        def __init__(self, **kwargs):
            captured["session_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, url, headers=None, timeout=15):
            captured["url"] = url
            captured["headers"] = dict(headers or {})
            captured["timeout"] = timeout
            return _FakeResponse(cookies={"sess": "abc123", "csrf": "xyz"})

    monkeypatch.setattr("maigret.activation.ClientSession", FakeSession)

    logger = Mock()
    await ParsingActivator.onlyfans(
        site,
        logger,
        url="https://onlyfans.com/api2/v2/users/adam",
    )

    # init request made
    assert captured["url"] == site.activation["url"]
    assert captured["timeout"] == 15
    assert captured["session_kwargs"] == {"trust_env": True}
    # headers passed to init include freshly generated time/sign
    assert "time" in captured["headers"]
    assert captured["headers"]["sign"].startswith("57203:")
    # cookie header populated from response
    assert site.headers["cookie"] == "sess=abc123; csrf=xyz"


@pytest.mark.asyncio
async def test_onlyfans_signature_is_deterministic_for_same_time(monkeypatch):
    """Two calls with patched time produce identical signatures."""
    site1 = _FakeSite(headers={"x-bc": "token", "cookie": "c=1"})
    site2 = _FakeSite(headers={"x-bc": "token", "cookie": "c=1"})

    import maigret.activation

    monkeypatch.setattr(maigret.activation, "_time", __import__("time"), raising=False)

    fixed = 1_700_000_000.123
    import time as time_mod

    monkeypatch.setattr(time_mod, "time", lambda: fixed)

    logger = Mock()
    await ParsingActivator.onlyfans(
        site1,
        logger,
        url="https://onlyfans.com/api2/v2/users/adam",
    )
    await ParsingActivator.onlyfans(
        site2,
        logger,
        url="https://onlyfans.com/api2/v2/users/adam",
    )

    assert site1.headers["time"] == site2.headers["time"]
    assert site1.headers["sign"] == site2.headers["sign"]


@pytest.mark.asyncio
async def test_onlyfans_sign_differs_per_path(monkeypatch):
    """Different target URLs must yield different signatures."""
    site = _FakeSite(headers={"x-bc": "token", "cookie": "c=1"})

    import time as time_mod

    monkeypatch.setattr(time_mod, "time", lambda: 1_700_000_000.0)

    logger = Mock()
    await ParsingActivator.onlyfans(
        site,
        logger,
        url="https://onlyfans.com/api2/v2/users/adam",
    )
    sig_adam = site.headers["sign"]

    await ParsingActivator.onlyfans(
        site,
        logger,
        url="https://onlyfans.com/api2/v2/users/bob",
    )
    sig_bob = site.headers["sign"]

    assert sig_adam != sig_bob


@pytest.mark.asyncio
async def test_proton_activation_sets_uid_and_bearer(monkeypatch):
    """Proton activator bootstraps an anon session and injects UID + Bearer token."""
    site = _FakeSite(
        headers={"X-Pm-Appversion": "web-account@5.0.398.1"},
        activation={"url": "https://account.proton.me/api/auth/v4/sessions"},
    )
    captured = {}

    class FakeSession:
        def __init__(self, **kwargs):
            captured["session_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers=None, json=None, timeout=None):
            captured["url"] = url
            captured["headers"] = dict(headers or {})
            captured["json"] = json
            captured["timeout"] = timeout
            return _FakeResponse(json_data={"UID": "uid123", "AccessToken": "tok456"})

    monkeypatch.setattr("maigret.activation.ClientSession", FakeSession)

    await ParsingActivator.proton(site, Mock(), timeout=7)

    assert captured["url"] == "https://account.proton.me/api/auth/v4/sessions"
    assert captured["headers"] == {"X-Pm-Appversion": "web-account@5.0.398.1"}
    assert captured["json"] == {}
    assert captured["timeout"] == 7
    assert site.headers["x-pm-uid"] == "uid123"
    assert site.headers["Authorization"] == "Bearer tok456"


@pytest.mark.asyncio
async def test_proton_activation_strips_stale_auth_from_bootstrap(monkeypatch):
    """A prior Authorization/x-pm-uid must not be sent to the session endpoint."""
    site = _FakeSite(
        headers={
            "X-Pm-Appversion": "web-account@5.0.398.1",
            "Authorization": "Bearer stale",
            "x-pm-uid": "stale-uid",
        },
        activation={"url": "https://account.proton.me/api/auth/v4/sessions"},
    )
    captured = {}

    class FakeSession:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers=None, json=None, timeout=None):
            captured["headers"] = dict(headers or {})
            return _FakeResponse(json_data={"UID": "u", "AccessToken": "t"})

    monkeypatch.setattr("maigret.activation.ClientSession", FakeSession)

    await ParsingActivator.proton(site, Mock())

    assert "Authorization" not in captured["headers"]
    assert "x-pm-uid" not in captured["headers"]
    assert site.headers["Authorization"] == "Bearer t"
    assert site.headers["x-pm-uid"] == "u"


@pytest.mark.asyncio
async def test_proton_activation_missing_token_leaves_headers_untouched(monkeypatch):
    """If Proton returns an error payload, do not inject broken auth headers."""
    site = _FakeSite(
        headers={"X-Pm-Appversion": "web-account@5.0.398.1"},
        activation={"url": "https://account.proton.me/api/auth/v4/sessions"},
    )

    class FakeSession:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers=None, json=None, timeout=None):
            return _FakeResponse(json_data={"Code": 5002, "Error": "Missing header"})

    monkeypatch.setattr("maigret.activation.ClientSession", FakeSession)

    logger = Mock()
    await ParsingActivator.proton(site, logger)

    assert "Authorization" not in site.headers
    assert "x-pm-uid" not in site.headers
    logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_wikimapia_activation_parses_token_from_challenge():
    """The Wikimapia activator reads the ngxsession token from the challenge
    body the checker already fetched and merges it into the request cookie."""
    site = Mock()
    site.name = "WikimapiaSearch"
    site.headers = {"Cookie": "verified=1"}

    challenge = (
        '<html><head><meta http-equiv="refresh" content="1"></head><body>'
        '<script>document.cookie="ngxsession=deadbeef0123456789";</script>'
        '</body></html>'
    )

    await ParsingActivator.wikimapia(site, Mock(), html=challenge)

    assert site.headers["Cookie"] == "verified=1; ngxsession=deadbeef0123456789"


@pytest.mark.asyncio
async def test_wikimapia_activation_replaces_stale_token():
    """A previously merged ngxsession is replaced, not duplicated, on re-activation."""
    site = Mock()
    site.name = "WikimapiaSearch"
    site.headers = {"Cookie": "verified=1; ngxsession=0000000000000000"}

    challenge = '<script>document.cookie="ngxsession=abcdef0123456789";</script>'

    await ParsingActivator.wikimapia(site, Mock(), html=challenge)

    assert site.headers["Cookie"] == "verified=1; ngxsession=abcdef0123456789"


@pytest.mark.asyncio
async def test_wikimapia_activation_no_token_leaves_cookie_untouched():
    """If the body carries no token, the cookie header is left as-is."""
    site = Mock()
    site.name = "WikimapiaSearch"
    site.headers = {"Cookie": "verified=1"}

    await ParsingActivator.wikimapia(site, Mock(), html="<html>no challenge here</html>")

    assert site.headers["Cookie"] == "verified=1"


@pytest.fixture
def activation_db(monkeypatch, tmp_path):
    """Two sites, one that mints tokens at runtime and one that doesn't."""
    db = MaigretDatabase()
    db.update_site(
        MaigretSite(
            'Twitter',
            {
                'url': 'https://twitter.com/{username}',
                'urlMain': 'https://twitter.com/',
                'activation': {'method': 'twitter', 'marks': ['nope']},
                'headers': {'x-guest-token': 'from-db', 'accept': 'text/html'},
            },
        )
    )
    db.update_site(
        MaigretSite(
            'Plain',
            {
                'url': 'https://example.com/{username}',
                'urlMain': 'https://example.com/',
                'headers': {'accept': 'text/html'},
            },
        )
    )
    monkeypatch.setattr(activation_cache, 'MAIGRET_HOME', str(tmp_path))
    monkeypatch.setattr(
        activation_cache, 'ACTIVATION_CACHE_PATH', str(tmp_path / 'activation.json')
    )
    return db


def test_activation_cache_persists_only_minted_headers(activation_db):
    """The database ships baseline headers; only what the run minted is cached.

    Storing the full header set would pin whatever the database shipped, so a
    later database update could never change those headers again.
    """
    logger = Mock()
    baseline = load_activation_cache(activation_db, logger)

    # simulate what ParsingActivator does mid-run
    activation_db.sites_dict['Twitter'].headers['x-guest-token'] = 'minted'

    save_activation_cache(activation_db, baseline, logger)

    written = json.loads(open(activation_cache.ACTIVATION_CACHE_PATH).read())
    assert written == {'Twitter': {'x-guest-token': 'minted'}}
    # the unchanged baseline header is not copied into the cache
    assert 'accept' not in written['Twitter']


def test_activation_cache_round_trip_applies_token(activation_db):
    logger = Mock()
    baseline = load_activation_cache(activation_db, logger)
    activation_db.sites_dict['Twitter'].headers['x-guest-token'] = 'minted'
    save_activation_cache(activation_db, baseline, logger)

    # a fresh run loads the database again, with the shipped value
    activation_db.sites_dict['Twitter'].headers['x-guest-token'] = 'from-db'
    load_activation_cache(activation_db, logger)

    assert activation_db.sites_dict['Twitter'].headers['x-guest-token'] == 'minted'


def test_activation_cache_skips_sites_without_activation(activation_db):
    logger = Mock()
    baseline = load_activation_cache(activation_db, logger)
    activation_db.sites_dict['Plain'].headers['accept'] = 'application/json'

    save_activation_cache(activation_db, baseline, logger)

    assert not os.path.exists(activation_cache.ACTIVATION_CACHE_PATH)


def test_activation_cache_ignores_corrupt_file(activation_db):
    logger = Mock()
    with open(activation_cache.ACTIVATION_CACHE_PATH, 'w') as f:
        f.write('{ this is not json')

    baseline = load_activation_cache(activation_db, logger)

    assert baseline['Twitter']['x-guest-token'] == 'from-db'
    assert activation_db.sites_dict['Twitter'].headers['x-guest-token'] == 'from-db'
    assert logger.debug.called


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions not supported on Windows")
def test_activation_cache_is_not_world_readable(activation_db):
    """The cache holds session credentials, so the umask must not decide."""
    logger = Mock()
    baseline = load_activation_cache(activation_db, logger)
    activation_db.sites_dict['Twitter'].headers['x-guest-token'] = 'minted'

    save_activation_cache(activation_db, baseline, logger)

    mode = os.stat(activation_cache.ACTIVATION_CACHE_PATH).st_mode & 0o777
    assert mode == 0o600, f"expected 0600, got {mode:o}"


def test_activation_cache_does_not_leak_into_shared_headers(monkeypatch, tmp_path):
    """MaigretSite.headers defaults to a mutable class attribute.

    A site with an activation block but no headers of its own shares that
    object with ~3000 other sites, so an in-place update would attach the
    cached token to every one of them.
    """
    logger = Mock()
    db = MaigretDatabase()
    db.update_site(
        MaigretSite(
            'NoHeaders',
            {
                'url': 'https://a.example/{username}',
                'urlMain': 'https://a.example/',
                'activation': {'method': 'twitter', 'marks': ['nope']},
            },
        )
    )
    db.update_site(
        MaigretSite(
            'Bystander',
            {'url': 'https://b.example/{username}', 'urlMain': 'https://b.example/'},
        )
    )
    cache_file = tmp_path / 'activation.json'
    cache_file.write_text(json.dumps({'NoHeaders': {'x-guest-token': 'secret'}}))
    monkeypatch.setattr(activation_cache, 'MAIGRET_HOME', str(tmp_path))
    monkeypatch.setattr(activation_cache, 'ACTIVATION_CACHE_PATH', str(cache_file))

    load_activation_cache(db, logger)

    assert db.sites_dict['NoHeaders'].headers['x-guest-token'] == 'secret'
    assert 'x-guest-token' not in db.sites_dict['Bystander'].headers
    assert 'x-guest-token' not in MaigretSite.headers
