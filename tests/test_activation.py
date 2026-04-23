"""Maigret activation test functions"""

import json
import yarl

import aiohttp
import pytest
from mock import Mock

from tests.conftest import LOCAL_SERVER_PORT
from maigret.activation import ParsingActivator, import_aiohttp_cookies

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
def test_vimeo_activation(default_db):
    vimeo_site = default_db.sites_dict['Vimeo']
    token1 = vimeo_site.headers['Authorization']

    ParsingActivator.vimeo(vimeo_site, Mock())
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
    def __init__(self, cookies=None):
        self.cookies = cookies or {}


def test_onlyfans_sets_xbc_when_zero(monkeypatch):
    site = _FakeSite(headers={"x-bc": "0", "cookie": "existing=1"})

    # Prevent any real network. If _sign path still fires requests.get, fail loudly.
    import maigret.activation as act_mod

    def boom(*a, **kw):  # pragma: no cover - sanity
        raise AssertionError("requests.get should not run when cookie is present")

    monkeypatch.setattr(act_mod.__dict__.get("requests", None) or __import__("requests"), "get", boom, raising=False)

    logger = Mock()
    ParsingActivator.onlyfans(site, logger, url="https://onlyfans.com/api2/v2/users/adam")

    # x-bc must be rewritten to a non-zero hex token
    assert site.headers["x-bc"] != "0"
    assert len(site.headers["x-bc"]) == 40  # 20 bytes → 40 hex chars
    # time / sign headers set for target URL
    assert "time" in site.headers and site.headers["time"].isdigit()
    assert site.headers["sign"].startswith("57203:")


def test_onlyfans_fetches_init_cookie_when_missing(monkeypatch):
    """When cookie header is absent, init endpoint is called and its cookies stored."""
    site = _FakeSite(headers={"x-bc": "already_set_token", "user-id": "0"})

    import requests

    captured = {}

    def fake_get(url, headers=None, timeout=15):
        captured["url"] = url
        captured["headers"] = dict(headers or {})
        return _FakeResponse(cookies={"sess": "abc123", "csrf": "xyz"})

    monkeypatch.setattr(requests, "get", fake_get)

    logger = Mock()
    ParsingActivator.onlyfans(site, logger, url="https://onlyfans.com/api2/v2/users/adam")

    # init request made
    assert captured["url"] == site.activation["url"]
    # headers passed to init include freshly generated time/sign
    assert "time" in captured["headers"]
    assert captured["headers"]["sign"].startswith("57203:")
    # cookie header populated from response
    assert site.headers["cookie"] == "sess=abc123; csrf=xyz"


def test_onlyfans_signature_is_deterministic_for_same_time(monkeypatch):
    """Two calls with patched time produce identical signatures."""
    site1 = _FakeSite(headers={"x-bc": "token", "cookie": "c=1"})
    site2 = _FakeSite(headers={"x-bc": "token", "cookie": "c=1"})

    import maigret.activation
    monkeypatch.setattr(maigret.activation, "_time", __import__("time"), raising=False)

    fixed = 1_700_000_000.123
    import time as time_mod
    monkeypatch.setattr(time_mod, "time", lambda: fixed)

    logger = Mock()
    ParsingActivator.onlyfans(site1, logger, url="https://onlyfans.com/api2/v2/users/adam")
    ParsingActivator.onlyfans(site2, logger, url="https://onlyfans.com/api2/v2/users/adam")

    assert site1.headers["time"] == site2.headers["time"]
    assert site1.headers["sign"] == site2.headers["sign"]


def test_onlyfans_sign_differs_per_path(monkeypatch):
    """Different target URLs must yield different signatures."""
    site = _FakeSite(headers={"x-bc": "token", "cookie": "c=1"})

    import time as time_mod
    monkeypatch.setattr(time_mod, "time", lambda: 1_700_000_000.0)

    logger = Mock()
    ParsingActivator.onlyfans(site, logger, url="https://onlyfans.com/api2/v2/users/adam")
    sig_adam = site.headers["sign"]

    ParsingActivator.onlyfans(site, logger, url="https://onlyfans.com/api2/v2/users/bob")
    sig_bob = site.headers["sign"]

    assert sig_adam != sig_bob
