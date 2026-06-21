"""Tests for the Cloudflare webgate config + checker."""

import json
from types import SimpleNamespace

from unittest.mock import Mock
import pytest

from maigret.checking import (
    CloudflareWebgateChecker,
    build_cloudflare_bypass_config,
)


def _settings(payload):
    return SimpleNamespace(cloudflare_bypass=payload)


def test_config_disabled_by_default():
    s = _settings({"enabled": False, "modules": [{"method": "json_api", "url": "x"}]})
    assert build_cloudflare_bypass_config(s, force_enable=False) is None


def test_config_force_enable_overrides_disabled_settings():
    s = _settings({"enabled": False, "modules": [{"method": "json_api", "url": "http://x:8191/v1"}]})
    cfg = build_cloudflare_bypass_config(s, force_enable=True)
    assert cfg is not None
    assert cfg["modules"][0]["url"] == "http://x:8191/v1"


def test_config_drops_invalid_modules():
    s = _settings({
        "enabled": True,
        "modules": [
            {"method": "url_rewrite", "url": "http://x:8000/html"},  # missing {url}
            {"method": "json_api", "url": "http://x:8191/v1"},
            {"method": "unknown", "url": "http://x"},
        ],
    })
    cfg = build_cloudflare_bypass_config(s)
    assert len(cfg["modules"]) == 1
    assert cfg["modules"][0]["method"] == "json_api"


def test_config_returns_none_when_no_valid_modules():
    s = _settings({"enabled": True, "modules": [{"method": "url_rewrite", "url": "no-placeholder"}]})
    assert build_cloudflare_bypass_config(s) is None


def test_config_default_trigger_protection():
    s = _settings({"enabled": True, "modules": [{"method": "json_api", "url": "http://x:8191/v1"}]})
    cfg = build_cloudflare_bypass_config(s)
    assert "cf_js_challenge" in cfg["trigger_protection"]
    assert "cf_firewall" in cfg["trigger_protection"]
    assert "webgate" in cfg["trigger_protection"]


@pytest.mark.asyncio
async def test_flaresolverr_success(httpserver):
    httpserver.expect_request("/v1", method="POST").respond_with_json({
        "status": "ok",
        "solution": {"status": 404, "response": "<html>missing</html>", "url": "https://site/missing"},
    })
    config = {
        "modules": [{"name": "fs", "method": "json_api", "url": httpserver.url_for("/v1")}],
        "session_prefix": "test",
    }
    c = CloudflareWebgateChecker(logger=Mock(), config=config)
    c.prepare(url="https://site/missing", timeout=5)
    body, status, err = await c.check()
    assert err is None
    assert status == 404  # upstream status preserved — fixes status_code checktype
    assert "missing" in body


@pytest.mark.asyncio
async def test_flaresolverr_solver_error_propagates(httpserver):
    httpserver.expect_request("/v1", method="POST").respond_with_json({
        "status": "error",
        "message": "Challenge could not be solved",
    })
    config = {
        "modules": [{"name": "fs", "method": "json_api", "url": httpserver.url_for("/v1")}],
    }
    c = CloudflareWebgateChecker(logger=Mock(), config=config)
    c.prepare(url="https://site/page", timeout=5)
    body, status, err = await c.check()
    assert err is not None
    assert "Challenge could not be solved" in err.desc


@pytest.mark.asyncio
async def test_falls_back_to_next_module_on_failure(httpserver):
    # Bind only the second module — the first is unreachable.
    httpserver.expect_request("/v1", method="POST").respond_with_json({
        "status": "ok",
        "solution": {"status": 200, "response": "ok-from-second", "url": "https://x"},
    })
    config = {
        "modules": [
            {"name": "broken", "method": "json_api", "url": "http://127.0.0.1:1/v1"},
            {"name": "good", "method": "json_api", "url": httpserver.url_for("/v1")},
        ],
    }
    c = CloudflareWebgateChecker(logger=Mock(), config=config)
    c.prepare(url="https://site/page", timeout=5)
    body, status, err = await c.check()
    assert err is None
    assert status == 200
    assert body == "ok-from-second"


@pytest.mark.asyncio
async def test_url_rewrite_returns_html_with_synthetic_200(httpserver):
    # CloudflareBypassForScraping returns just the rendered HTML, no JSON wrapper.
    httpserver.expect_request("/html").respond_with_data(
        "<html>profile body</html>", status=200, content_type="text/html"
    )
    config = {
        "modules": [{
            "name": "cbfs",
            "method": "url_rewrite",
            "url": httpserver.url_for("/html") + "?url={url}",
        }],
    }
    c = CloudflareWebgateChecker(logger=Mock(), config=config)
    c.prepare(url="https://site/page", timeout=5)
    body, status, err = await c.check()
    assert err is None
    assert status == 200  # synthetic — url_rewrite cannot recover real status
    assert "profile body" in body


@pytest.mark.asyncio
async def test_all_modules_unreachable_actionable_error():
    """When every module fails with 'Webgate unreachable' (TCP/DNS refused at
    the configured URL), the user almost certainly opted into cloudflare_bypass
    and forgot to start the solver. Surface that fact explicitly so the user
    knows it's their config, not a Maigret bug."""
    config = {
        "modules": [
            {"name": "fs", "method": "json_api", "url": "http://127.0.0.1:1/v1"},
            {"name": "cbfs", "method": "url_rewrite", "url": "http://127.0.0.1:2/html?url={url}"},
        ],
    }
    c = CloudflareWebgateChecker(logger=Mock(), config=config)
    c.prepare(url="https://site/page", timeout=2)
    body, status, err = await c.check()
    assert err is not None
    assert err.type == "Webgate unavailable"
    # The opt-in nature of cloudflare_bypass must be explicit — the user needs
    # to understand the error came from THEIR enabling it, not Maigret guessing.
    assert "cloudflare_bypass is enabled" in err.desc
    assert "--cloudflare-bypass" in err.desc
    # Per-module attempt summary still helps users see WHICH backend failed
    assert "fs:Webgate unreachable" in err.desc
    assert "cbfs:Webgate unreachable" in err.desc
    # Primary URL is shown so the user knows where to look
    assert "http://127.0.0.1:1/v1" in err.desc
    # FlareSolverr docker hint when primary is json_api
    assert "flaresolverr" in err.desc.lower()
    # The escape hatch — disabling — must be mentioned for users who don't
    # want to run the solver at all.
    assert "disable cloudflare_bypass" in err.desc


@pytest.mark.asyncio
async def test_mixed_failure_modes_keep_generic_summary(monkeypatch):
    """If some modules fail with a non-reachability error (e.g. the solver IS
    running but returned a 500 / timeout), the 'opted-in but unreachable'
    framing would be misleading. Fall back to the generic summary."""
    from maigret import checking as checking_module
    from maigret.errors import CheckError

    config = {
        "modules": [
            {"name": "fs", "method": "json_api", "url": "http://127.0.0.1:1/v1"},
            {"name": "cbfs", "method": "url_rewrite", "url": "http://127.0.0.1:2/html?url={url}"},
        ],
    }
    c = CloudflareWebgateChecker(logger=Mock(), config=config)
    c.prepare(url="https://site/page", timeout=2)

    # Force the FIRST module to fail with a non-reachability error so the
    # all_unreachable branch is bypassed.
    async def fake_flaresolverr(self, module):
        return None, 0, CheckError("Solver error", "FlareSolverr returned 500")
    monkeypatch.setattr(checking_module.CloudflareWebgateChecker,
                        '_check_flaresolverr', fake_flaresolverr)

    body, status, err = await c.check()
    assert err is not None
    assert err.type == "Webgate unavailable"
    # Mixed failure → must NOT use the opted-in wording (it implies "the
    # solver isn't reachable", which isn't true here — it's reachable but
    # broken).
    assert "cloudflare_bypass is enabled" not in err.desc
    # The generic summary still surfaces the failed module names
    assert "fs:Solver error" in err.desc


@pytest.mark.asyncio
async def test_session_is_scoped_per_host(httpserver):
    seen_sessions = []

    def handler(request):
        seen_sessions.append(request.get_json()["session"])
        return {"status": "ok", "solution": {"status": 200, "response": "", "url": "x"}}

    httpserver.expect_request("/v1", method="POST").respond_with_handler(handler)
    config = {"modules": [{"name": "fs", "method": "json_api", "url": httpserver.url_for("/v1")}]}
    c = CloudflareWebgateChecker(logger=Mock(), config=config)

    c.prepare(url="https://patreon.com/foo", timeout=5)
    await c.check()
    c.prepare(url="https://patreon.com/bar", timeout=5)
    await c.check()
    c.prepare(url="https://lomography.com/baz", timeout=5)
    await c.check()

    assert seen_sessions[0] == seen_sessions[1], "same host -> same session"
    assert seen_sessions[0] != seen_sessions[2], "different host -> different session"
    assert "patreon.com" in seen_sessions[0]
    assert "lomography.com" in seen_sessions[2]


@pytest.mark.asyncio
async def test_flaresolverr_request_body_shape(httpserver):
    captured = {}

    def handler(request):
        captured["body"] = request.get_json()
        return {"status": "ok", "solution": {"status": 200, "response": "", "url": "x"}}

    httpserver.expect_request("/v1", method="POST").respond_with_handler(handler)
    config = {"modules": [{"name": "fs", "method": "json_api", "url": httpserver.url_for("/v1")}]}
    c = CloudflareWebgateChecker(logger=Mock(), config=config)
    c.prepare(url="https://site/page", headers={"User-Agent": "test-ua/1.0"}, timeout=5)
    await c.check()
    body = captured["body"]
    assert body["cmd"] == "request.get"
    assert body["url"] == "https://site/page"
    assert body["session"].startswith("maigret-")
    # userAgent was removed in FlareSolverr v2; the impersonated browser's
    # own UA must be used to keep TLS+UA consistent.
    assert "userAgent" not in body
    assert "proxy" not in body


@pytest.mark.asyncio
async def test_flaresolverr_proxy_string_passed_through(httpserver):
    captured = {}

    def handler(request):
        captured["body"] = request.get_json()
        return {"status": "ok", "solution": {"status": 200, "response": "", "url": "x"}}

    httpserver.expect_request("/v1", method="POST").respond_with_handler(handler)
    config = {
        "modules": [
            {
                "name": "fs",
                "method": "json_api",
                "url": httpserver.url_for("/v1"),
                "proxy": "socks5://localhost:1080",
            }
        ]
    }
    c = CloudflareWebgateChecker(logger=Mock(), config=config)
    c.prepare(url="https://site/page", headers={}, timeout=5)
    await c.check()
    assert captured["body"]["proxy"] == {"url": "socks5://localhost:1080"}


@pytest.mark.asyncio
async def test_flaresolverr_proxy_dict_with_credentials(httpserver):
    captured = {}

    def handler(request):
        captured["body"] = request.get_json()
        return {"status": "ok", "solution": {"status": 200, "response": "", "url": "x"}}

    httpserver.expect_request("/v1", method="POST").respond_with_handler(handler)
    config = {
        "modules": [
            {
                "name": "fs",
                "method": "json_api",
                "url": httpserver.url_for("/v1"),
                "proxy": {
                    "url": "http://proxy.example:3128",
                    "username": "u",
                    "password": "p",
                    "stripped_extra": "ignored",
                },
            }
        ]
    }
    c = CloudflareWebgateChecker(logger=Mock(), config=config)
    c.prepare(url="https://site/page", headers={}, timeout=5)
    await c.check()
    proxy = captured["body"]["proxy"]
    assert proxy == {"url": "http://proxy.example:3128", "username": "u", "password": "p"}
