"""Local HTTP CONNECT/SOCKS peers; no real websites or external proxies."""

import asyncio
import base64
import json
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator
from urllib.parse import urlsplit
from unittest.mock import Mock

import pytest
from aiohttp import ClientSession

from maigret.activation import ParsingActivator
from maigret import activation as activation_cache
from maigret.maigret import main
from maigret.checking import CurlCffiChecker, SimpleAiohttpChecker, maigret
from maigret.result import MaigretCheckStatus
from maigret.sites import MaigretDatabase, MaigretSite


class LocalProxy:
    def __init__(self, scheme: str, token: str = "test-token") -> None:
        self.scheme = scheme
        self.token = token
        self.requests: list[tuple[str, str, dict[str, str], bytes]] = []
        self.destinations: list[str] = []
        self.connections: set[asyncio.Task[Any]] = set()
        self.activation_seen = asyncio.Event()
        self.failure = ""
        self.redirect = False
        self.activation_redirect = False
        self.connect_status = 200
        self.response_status = 200
        self.reject_activation_connect = 0
        self.auth: tuple[str, str] | None = None
        self.authenticated: list[bool] = []
        self.url = ""

    async def handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        task = asyncio.current_task()
        assert task is not None
        self.connections.add(task)
        try:
            if self.scheme.startswith("socks5"):
                version, count = await reader.readexactly(2)
                assert version == 5
                await reader.readexactly(count)
                writer.write(b"\x05\x02" if self.auth else b"\x05\x00")
                await writer.drain()
                if self.auth:
                    assert (await reader.readexactly(1)) == b"\x01"
                    size = (await reader.readexactly(1))[0]
                    username = (await reader.readexactly(size)).decode()
                    size = (await reader.readexactly(1))[0]
                    password = (await reader.readexactly(size)).decode()
                    self.authenticated.append((username, password) == self.auth)
                    writer.write(b"\x01\x00")
                    await writer.drain()
                prefix = await reader.readexactly(4)
                assert (
                    prefix == b"\x05\x01\x00\x03"
                ), "DNS must be resolved at the proxy"
                size = (await reader.readexactly(1))[0]
                host = (await reader.readexactly(size)).decode()
                port = int.from_bytes(await reader.readexactly(2), "big")
                self.destinations.append(f"{host}:{port}")
                writer.write(b"\x05\x00\x00\x01\x7f\x00\x00\x01\x00\x50")
                await writer.drain()
            else:
                first = await reader.readuntil(b"\r\n\r\n")
                if first.startswith(b"CONNECT "):
                    self.record_auth(first)
                    self.destinations.append(first.split(b" ")[1].decode())
                    status = (
                        self.reject_activation_connect
                        if len(self.destinations) > 1 and self.reject_activation_connect
                        else self.connect_status
                    )
                    writer.write(f"HTTP/1.1 {status} Tunnel\r\n\r\n".encode())
                    await writer.drain()
                    if status != 200:
                        return
                else:
                    self.record_auth(first)
                    await self.respond(first, reader, writer)
                    return
            await self.respond(await reader.readuntil(b"\r\n\r\n"), reader, writer)
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()
            self.connections.discard(task)

    def record_auth(self, raw: bytes) -> None:
        if self.auth:
            expected = base64.b64encode(":".join(self.auth).encode())
            self.authenticated.append(b"Proxy-Authorization: Basic " + expected in raw)

    async def respond(
        self, raw: bytes, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        lines = raw.decode().split("\r\n")
        method, target, _ = lines[0].split(" ")
        headers = dict(
            line.lower().split(": ", 1) for line in lines[1:] if ": " in line
        )
        body = await reader.readexactly(int(headers.get("content-length", "0")))
        path = urlsplit(target).path
        self.requests.append((method, path, headers, body))
        status = self.response_status
        extra = ""
        if self.activation_redirect and path == "/activate":
            status = 302
            extra = "Location: http://redirect.invalid/activate-final\r\n"
            content = ""
        elif path.startswith("/activate"):
            self.activation_seen.set()
            if self.failure == "timeout":
                await reader.read()
                return
            if self.failure == "disconnect":
                return
            if self.failure == "malformed":
                content = "{}"
            else:
                content = json.dumps(
                    {
                        "guest_token": self.token,
                        "jwt": self.token,
                        "UID": "uid",
                        "AccessToken": self.token,
                        "data": {"sub": self.token, "subp": "subp"},
                    }
                )
            if self.failure != "malformed":
                extra = f"Set-Cookie: session={self.token}; Path=/\r\n"
        elif self.redirect and path != "/redirected":
            status = 302
            extra = "Location: http://redirect.invalid/redirected\r\n"
            content = ""
        elif any(
            self.token in headers.get(key, "")
            for key in ("authorization", "x-guest-token", "cookie")
        ):
            content = "PROFILE"
        else:
            content = 'CHALLENGE document.cookie="ngxsession=deadbeef"'
        payload = content.encode()
        writer.write(
            f"HTTP/1.1 {status} Test\r\nContent-Type: application/json\r\n"
            f"Content-Length: {len(payload)}\r\nConnection: close\r\n{extra}\r\n".encode()
            + payload
        )
        await writer.drain()


@asynccontextmanager
async def proxy_peer(
    scheme: str = "http", token: str = "test-token"
) -> AsyncIterator[LocalProxy]:
    peer = LocalProxy(scheme, token)
    server = await asyncio.start_server(peer.handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    peer.url = f"{scheme}://127.0.0.1:{port}"
    try:
        yield peer
    finally:
        server.close()
        await server.wait_closed()
        tasks = list(peer.connections)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def activation_site(method: str, protocol: str = "", curl: bool = False) -> MaigretSite:
    return MaigretSite(
        "Local",
        {
            "url": "http://profile.invalid/users/{username}",
            "urlMain": "http://profile.invalid",
            "protocol": protocol,
            "checkType": "message",
            "presenseStrs": ["PROFILE"],
            "headers": {},
            "protection": ["tls_fingerprint"] if curl else [],
            "activation": {
                "method": method,
                "url": "http://activation.invalid/activate",
                "marks": ["CHALLENGE"],
                "src": "guest_token",
                "static_param": "static",
                "checksum_indexes": [0, 1],
                "checksum_constant": 0,
                "format": "{}:{:x}",
            },
        },
    )


async def scan(site: MaigretSite, proxy: str, **kwargs: Any) -> dict[str, Any]:
    return await maigret(
        "alice",
        {site.name: site},
        logging.getLogger("proxy-test"),
        proxy=proxy,
        no_progressbar=True,
        timeout=0.5,
        **kwargs,
    )


@pytest.mark.parametrize("scheme", ["http", "socks5", "socks5h"])
@pytest.mark.parametrize("method", ["twitter", "vimeo", "onlyfans", "proton", "weibo"])
@pytest.mark.parametrize("curl", [False, True])
async def test_scan_routes_activation_and_retry(
    scheme: str, method: str, curl: bool
) -> None:
    async with proxy_peer(scheme) as peer:
        site = activation_site(method, curl=curl)
        result = (await scan(site, peer.url))["Local"]
        assert result["status"].status == MaigretCheckStatus.CLAIMED
        assert [r[1] for r in peer.requests] == [
            "/users/alice",
            "/activate",
            "/users/alice",
        ]
        initial, activation, retry = peer.requests
        assert activation[0] == ("GET" if method in ("vimeo", "onlyfans") else "POST")
        assert "test-token" not in str(initial[2])
        assert "test-token" in str(retry[2])
        if method == "proton":
            assert activation[3] == b"{}"
            assert retry[2]["x-pm-uid"] == "uid"
        if method == "weibo":
            assert activation[3] == b"cb=visitor_gray_callback&tid=&from=weibo"
            assert retry[2]["cookie"] == "sub=test-token; subp=subp"
        if method == "onlyfans":
            assert "sign" in activation[2] and "sign" in retry[2]
            assert activation[2]["sign"] != retry[2]["sign"]


@pytest.mark.parametrize("protocol", ["tor", "i2p"])
@pytest.mark.parametrize("curl", [False, True])
async def test_activation_inherits_protocol_route(protocol: str, curl: bool) -> None:
    async with proxy_peer() as clearweb, proxy_peer() as routed:
        site = activation_site("twitter", protocol, curl)
        result = await scan(site, clearweb.url, **{f"{protocol}_proxy": routed.url})
        assert result["Local"]["status"].status == MaigretCheckStatus.CLAIMED
        assert clearweb.requests == []
        assert len(routed.requests) == 3


@pytest.mark.parametrize("checker_type", [SimpleAiohttpChecker, CurlCffiChecker])
async def test_explicit_route_overrides_environment_and_redirects(
    checker_type: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with proxy_peer() as selected, proxy_peer() as environment:
        selected.redirect = True
        for key in (
            "http_proxy",
            "HTTP_PROXY",
            "https_proxy",
            "HTTPS_PROXY",
            "ALL_PROXY",
        ):
            monkeypatch.setenv(key, environment.url)
        for key in ("no_proxy", "NO_PROXY"):
            monkeypatch.setenv(key, "*")
        checker = checker_type(proxy=selected.url, logger=Mock())
        checker.prepare("http://profile.invalid/users/alice", timeout=1)
        _, status, error = await checker.check()
        assert error is None and status == 200
        assert [r[1] for r in selected.requests] == ["/users/alice", "/redirected"]
        assert environment.requests == []


@pytest.mark.parametrize("failure", ["timeout", "disconnect", "malformed"])
@pytest.mark.parametrize("method", ["twitter", "vimeo", "onlyfans", "proton", "weibo"])
async def test_activation_failure_is_unknown(
    failure: str, method: str, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    async with proxy_peer(token="secret-activation-token") as peer:
        peer.failure = failure
        result = (await scan(activation_site(method), peer.url))["Local"]
        assert result["status"].status == MaigretCheckStatus.UNKNOWN
        assert result["status"].error is not None
        assert peer.requests[0][1] == "/users/alice"
        assert len(peer.requests) >= 2
        assert all(r[1] == "/activate" for r in peer.requests[1:])
        assert "secret-activation-token" not in caplog.text


@pytest.mark.parametrize("curl", [False, True])
async def test_activation_redirect_ignores_environment(
    curl: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    async with proxy_peer() as selected, proxy_peer() as environment:
        selected.activation_redirect = True
        monkeypatch.setenv("http_proxy", environment.url)
        monkeypatch.setenv("HTTP_PROXY", environment.url)
        monkeypatch.setenv("NO_PROXY", "*")
        monkeypatch.setenv("no_proxy", "*")
        result = await scan(activation_site("twitter", curl=curl), selected.url)
        assert result["Local"]["status"].status == MaigretCheckStatus.CLAIMED
        assert [r[1] for r in selected.requests] == [
            "/users/alice",
            "/activate",
            "/activate-final",
            "/users/alice",
        ]
        assert not environment.requests


async def test_failed_activation_never_falls_back_to_reachable_origin() -> None:
    async with proxy_peer() as selected, proxy_peer() as origin:
        selected.failure = "disconnect"
        site = activation_site("twitter")
        site.activation["url"] = origin.url + "/activate"
        result = await scan(site, selected.url)
        assert result["Local"]["status"].status == MaigretCheckStatus.UNKNOWN
        assert not origin.requests


@pytest.mark.parametrize("status", [403, 407])
async def test_activation_connect_rejection_is_unknown(status: int) -> None:
    async with proxy_peer() as peer:
        peer.reject_activation_connect = status
        result = (await scan(activation_site("twitter"), peer.url))["Local"]
        assert result["status"].status == MaigretCheckStatus.UNKNOWN
        assert result["status"].error is not None
        assert [r[1] for r in peer.requests] == ["/users/alice"]


@pytest.mark.parametrize("scheme", ["http", "socks5", "socks5h"])
@pytest.mark.parametrize("curl", [False, True])
async def test_proxy_credentials_preserved_without_logging_secrets(
    scheme: str, curl: bool, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    async with proxy_peer(scheme, token="activation-secret") as peer:
        peer.auth = ("proxy-user", "proxy-password")
        proxy = peer.url.replace("://", "://proxy-user:proxy-password@")
        result = await scan(activation_site("vimeo", curl=curl), proxy)
        assert result["Local"]["status"].status == MaigretCheckStatus.CLAIMED
        assert peer.authenticated == [True, True, True]
        for secret in (proxy, "proxy-user", "proxy-password", "activation-secret"):
            assert secret not in caplog.text


@pytest.mark.parametrize("status", [403, 407])
@pytest.mark.parametrize("checker_type", [SimpleAiohttpChecker, CurlCffiChecker])
async def test_connect_rejection_is_technical(status: int, checker_type: type) -> None:
    async with proxy_peer() as peer:
        peer.connect_status = status
        checker = checker_type(proxy=peer.url, logger=Mock())
        checker.prepare("https://profile.invalid/users/alice", timeout=0.5)
        html, code, error = await checker.check()
        assert error is not None and code == 0
        assert not html
        assert peer.requests == []
        assert peer.destinations


@pytest.mark.parametrize("checker_type", [SimpleAiohttpChecker, CurlCffiChecker])
async def test_forward_proxy_authentication_failure_is_technical(
    checker_type: type,
) -> None:
    async with proxy_peer() as peer:
        peer.response_status = 407
        checker = checker_type(proxy=peer.url, logger=Mock())
        checker.prepare("http://profile.invalid/users/alice", timeout=0.5)
        html, status, error = await checker.check()
        assert error is not None and error.type == "Proxy"
        assert status == 0 and not html


async def test_concurrent_scans_do_not_mutate_shared_site() -> None:
    site = activation_site("twitter")
    async with proxy_peer(token="first-token") as first, proxy_peer(
        token="second-token"
    ) as second:
        results = await asyncio.gather(scan(site, first.url), scan(site, second.url))
        for result, peer in zip(results, (first, second)):
            assert result["Local"]["status"].status == MaigretCheckStatus.CLAIMED
            assert result["Local"]["site"].headers["x-guest-token"] == peer.token
            assert len(peer.requests) == 3
        assert site.headers == {}
        assert MaigretSite.headers == {}


async def test_returned_activation_state_can_be_explicitly_cached(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    site = activation_site("twitter")
    database = MaigretDatabase()
    database.update_site(site)
    cache_file = tmp_path / "activation.json"
    monkeypatch.setattr(activation_cache, "ACTIVATION_CACHE_PATH", str(cache_file))
    baseline = activation_cache.load_activation_cache(database, Mock())
    async with proxy_peer() as peer:
        result = await scan(site, peer.url)
    runtime_database = MaigretDatabase()
    runtime_database.update_site(result["Local"]["site"])
    activation_cache.save_activation_cache(runtime_database, baseline, Mock())
    assert json.loads(cache_file.read_text()) == {
        "Local": {"x-guest-token": "test-token"}
    }
    assert site.headers == {}


@pytest.mark.parametrize("route", ["direct", "explicit", "environment"])
async def test_cli_keeps_proxy_tokens_out_of_global_cache(
    route: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli_logger = logging.getLogger("maigret")
    monkeypatch.setattr(cli_logger, "level", cli_logger.level)
    cache_file = tmp_path / "activation.json"
    cache_file.write_text(json.dumps({"Local": {"x-guest-token": "old-cache-token"}}))
    monkeypatch.setattr(activation_cache, "ACTIVATION_CACHE_PATH", str(cache_file))
    monkeypatch.chdir(tmp_path)
    async with proxy_peer() as peer:
        site = activation_site("twitter")
        site.url = peer.url + "/users/{username}"
        site.url_main = peer.url
        site.activation["url"] = peer.url + "/activate"
        database = MaigretDatabase()
        database.update_site(site)
        db_file = tmp_path / "database.json"
        database.save_to_file(str(db_file))
        args = [
            "maigret",
            "alice",
            "--db",
            str(db_file),
            "--no-autoupdate",
            "--no-progressbar",
            "--no-recursion",
            "--no-extracting",
        ]
        if route != "direct":
            peer.auth = ("proxy-user", "proxy-password")
            proxy_url = peer.url.replace("://", "://proxy-user:proxy-password@")
            if route == "explicit":
                args += ["--proxy", proxy_url]
            else:
                monkeypatch.setenv("http_proxy", proxy_url)
                monkeypatch.setenv("no_proxy", "")
                monkeypatch.setenv("NO_PROXY", "")
        monkeypatch.setattr(sys, "argv", args)
        await main()
        assert peer.requests[0][2].get("x-guest-token") == (
            "old-cache-token" if route == "direct" else None
        )
    expected_token = "test-token" if route == "direct" else "old-cache-token"
    assert json.loads(cache_file.read_text()) == {
        "Local": {"x-guest-token": expected_token}
    }
    assert "proxy-password" not in capsys.readouterr().out


async def test_cancellation_closes_activation_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with proxy_peer() as peer:
        peer.failure = "timeout"
        closing = asyncio.Event()
        release = asyncio.Event()
        original_close = ClientSession.close

        async def delayed_close(session: ClientSession) -> None:
            if peer.activation_seen.is_set():
                closing.set()
                await release.wait()
            await original_close(session)

        monkeypatch.setattr(ClientSession, "close", delayed_close)
        task = asyncio.create_task(scan(activation_site("twitter"), peer.url))
        await asyncio.wait_for(peer.activation_seen.wait(), 2)
        task.cancel()
        await asyncio.wait_for(closing.wait(), 2)
        await asyncio.sleep(0)
        try:
            assert not task.done(), "scan must await transport cleanup before returning"
        finally:
            release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        for _ in range(100):
            if not peer.connections:
                break
            await asyncio.sleep(0.01)
        assert not peer.connections


async def test_onlyfans_existing_cookie_skips_initialization() -> None:
    site = activation_site("onlyfans")
    site.headers["cookie"] = "session=existing"
    await ParsingActivator.onlyfans(
        site, Mock(), proxy="http://127.0.0.1:1", url=site.url
    )
    assert site.headers["cookie"] == "session=existing"
    assert site.headers["sign"]


async def test_wikimapia_is_network_free() -> None:
    site = activation_site("wikimapia")
    await ParsingActivator.wikimapia(
        site,
        Mock(),
        proxy="http://127.0.0.1:1",
        html='document.cookie="ngxsession=deadbeef"',
    )
    assert site.headers["Cookie"] == "ngxsession=deadbeef"


@pytest.mark.parametrize("checker_type", [SimpleAiohttpChecker, CurlCffiChecker])
async def test_unsupported_proxy_is_rejected(checker_type: type) -> None:
    with pytest.raises(ValueError, match="Unsupported proxy scheme"):
        checker_type(
            proxy="ftp://secret-user:secret-password@127.0.0.1:1", logger=Mock()
        )
